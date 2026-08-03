import os
import json
import uuid
import time
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from playwright.sync_api import Browser

from src.config import SCREENSHOTS_DIR, HEALING_THRESHOLD, PLAYWRIGHT_TIMEOUT
from src.parser import parse_test_case_with_llm, TestStep
from src.executor import execute_step
from src.self_healing import SelfHealingLocator
from src.reporter import generate_report

logger = logging.getLogger(__name__)

# database persistence is handled by the calling route handler in main.py

def run_test_case(
    test_case_text: str,
    browser: Browser,
    self_healing_enabled: bool = True,
    log_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Orchestrates the entire run of a single natural language test case.
    Reuses the active Playwright Browser instance by creating a clean context & page.
    """
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:6]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    log(f"Starting test execution. Run ID: {run_id}")
    log(f"Natural language test scenario: '{test_case_text}'")
    log(f"Self-healing: {'ENABLED' if self_healing_enabled else 'DISABLED'}")

    run_data = {
        "run_id": run_id,
        "timestamp": timestamp,
        "test_case_text": test_case_text,
        "status": "FAILED",
        "duration": 0.0,
        "steps": [],
        "healing_logs": []
    }

    # Step 1: Parse test case
    log("Invoking local LLM to parse natural language scenario...")
    start_parse_time = time.time()
    try:
        parsed_steps = parse_test_case_with_llm(test_case_text)
        log(f"Parsed {len(parsed_steps)} steps from the scenario (Took {time.time() - start_parse_time:.2f}s).")
    except Exception as e:
        error_msg = f"Parsing failed: {e}"
        log(error_msg)
        run_data["error"] = error_msg
        save_to_db(run_data)
        return run_data

    # Step 2: Create browser page context
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    
    # Store page-specific logs to track steps details
    execution_steps = []
    healing_logs = []
    
    start_time = time.time()
    overall_status = "PASSED"

    for idx, raw_step in enumerate(parsed_steps):
        step = raw_step.model_copy()  # Create a copy so modifications don't mutate original
        step_num = idx + 1
        log(f"[{step_num}/{len(parsed_steps)}] Step: {step.description}")
        
        step_run = {
            "description": step.description,
            "action": step.action,
            "target": step.target,
            "value": step.value,
            "status": "PENDING",
            "error": None,
            "screenshot": None,
            "duration": 0.0
        }
        
        step_start = time.time()
        
        try:
            # Attempt to execute the step normally
            execute_step(page, step, timeout=PLAYWRIGHT_TIMEOUT)
            step_run["status"] = "PASSED"
            log(f"[{step_num}/{len(parsed_steps)}] Step passed.")
            
        except Exception as primary_error:
            # Primary execution failed
            error_repr = str(primary_error)
            log(f"[{step_num}/{len(parsed_steps)}] Action failed: {error_repr}")
            
            # Check if self-healing can be applied
            is_healable = step.action not in ["navigate", "assert_url"]
            if self_healing_enabled and is_healable:
                log(f"[{step_num}/{len(parsed_steps)}] Initiating self-healing locator protocol...")
                
                try:
                    healed_candidate, confidence = SelfHealingLocator.heal(
                        page, step.target, threshold=HEALING_THRESHOLD
                    )
                    
                    if healed_candidate:
                        healed_repr = SelfHealingLocator.build_representation(healed_candidate)
                        healed_sel = healed_candidate["selector"]
                        
                        log(f"[{step_num}/{len(parsed_steps)}] Self-healing MATCH FOUND!")
                        log(f"  Healed to: '{healed_sel}' (Confidence: {confidence * 100:.1f}%)")
                        
                        # Save healing details
                        healing_log = {
                            "step_index": step_num,
                            "step_description": step.description,
                            "action": step.action,
                            "original_target": step.target,
                            "healed_selector": healed_sel,
                            "healed_representation": healed_repr,
                            "confidence": confidence
                        }
                        healing_logs.append(healing_log)
                        
                        # Update the step's locator to the healed one
                        step.target = healed_sel
                        
                        # Retry the execution with the healed locator
                        log(f"[{step_num}/{len(parsed_steps)}] Retrying step execution with healed locator...")
                        execute_step(page, step, timeout=PLAYWRIGHT_TIMEOUT)
                        
                        step_run["status"] = "HEALED"
                        step_run["target"] = healed_sel  # Save healed selector in results
                        log(f"[{step_num}/{len(parsed_steps)}] Step healed and passed successfully.")
                    else:
                        # Healing failed to find any matching element
                        log(f"[{step_num}/{len(parsed_steps)}] Self-healing did not find any matches above threshold.")
                        raise primary_error
                        
                except Exception as healing_error:
                    log(f"[{step_num}/{len(parsed_steps)}] Step execution failed permanently. Error: {healing_error}")
                    step_run["status"] = "FAILED"
                    step_run["error"] = str(healing_error)
                    overall_status = "FAILED"
                    
                    # Capture failure screenshot
                    screenshot_filename = f"fail_{run_id}_step_{step_num}.png"
                    screenshot_path = SCREENSHOTS_DIR / screenshot_filename
                    try:
                        page.screenshot(path=screenshot_path, timeout=2000)
                        step_run["screenshot"] = screenshot_filename
                        log(f"Captured failure screenshot saved to: {screenshot_path}")
                    except Exception as screenshot_err:
                        logger.error(f"Failed to capture screenshot: {screenshot_err}")
            else:
                # No self-healing enabled or step is not healable
                step_run["status"] = "FAILED"
                step_run["error"] = error_repr
                overall_status = "FAILED"
                
                # Capture failure screenshot
                screenshot_filename = f"fail_{run_id}_step_{step_num}.png"
                screenshot_path = SCREENSHOTS_DIR / screenshot_filename
                try:
                    page.screenshot(path=screenshot_path, timeout=2000)
                    step_run["screenshot"] = screenshot_filename
                    log(f"Captured failure screenshot saved to: {screenshot_path}")
                except Exception as screenshot_err:
                    logger.error(f"Failed to capture screenshot: {screenshot_err}")
                    
        step_run["duration"] = time.time() - step_start
        execution_steps.append(step_run)
        
        # Break execution flow on step failure
        if step_run["status"] == "FAILED":
            break

    duration = time.time() - start_time
    log(f"Execution finished in {duration:.2f}s. Result: {overall_status}")
    
    # Close tab context
    context.close()
    
    # Compile run data
    run_data["status"] = overall_status
    run_data["duration"] = duration
    run_data["steps"] = execution_steps
    run_data["healing_logs"] = healing_logs
    
    # Generate HTML report
    try:
        report_file = generate_report(run_data)
        run_data["report_file"] = report_file
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        traceback.print_exc()
        run_data["report_file"] = None

    # Return run_data directly to backend orchestrator
    return run_data
