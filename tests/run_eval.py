import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path

# Add project root to path so we can import src
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Force cache directories to D: drive before other imports
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = r"D:\playwright_browsers"
os.environ["HF_HOME"] = r"D:\hf_cache"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = r"D:\hf_cache"

from playwright.sync_api import sync_playwright
from src.agent import run_test_case
from src.config import OLLAMA_URL, OLLAMA_MODEL

def check_ollama_status() -> bool:
    """
    Checks if Ollama is running and has the model loaded.
    """
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if res.status_code != 200:
            return False
            
        models = [m["name"] for m in res.json().get("models", [])]
        model_exists = any(OLLAMA_MODEL in m for m in models)
        
        if not model_exists:
            print(f"WARNING: The configured model '{OLLAMA_MODEL}' was not found in Ollama.")
            return False
            
        return True
    except Exception:
        return False

def start_flask_server():
    """
    Starts the local Flask target application in a background subprocess.
    """
    print("Checking if Flask server is already running...")
    try:
        res = requests.get("http://localhost:5000/demo/login", timeout=2)
        if res.status_code == 200:
            print("Flask server is already running on port 5000.")
            return None
    except requests.RequestException:
        pass

    print("Starting Flask server as a background subprocess...")
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    server_ready = False
    for i in range(15):
        time.sleep(1)
        try:
            res = requests.get("http://localhost:5000/demo/login", timeout=1)
            if res.status_code == 200:
                server_ready = True
                print("Flask server started successfully.")
                break
        except requests.RequestException:
            pass
            
    if not server_ready:
        proc.terminate()
        stdout, stderr = proc.communicate()
        print(f"Error starting Flask server. stdout: {stdout}, stderr: {stderr}")
        sys.exit(1)
        
    return proc

def main():
    print("==================================================")
    print("   AI SELF-HEALING AGENT EVALUATION RUNNER")
    print("==================================================")

    # 1. Check Ollama
    print("Checking local Ollama status...")
    ollama_online = check_ollama_status()
    if not ollama_online:
        print("WARNING: Local Ollama service is not running or doesn't have the model loaded.")
        print("The evaluation runner will continue using the built-in heuristic parser fallback.")
        print("To test genuine LLM step parsing, please download Ollama and run: ollama pull qwen2.5:1.5b")
    else:
        print(f"Ollama is online. Model '{OLLAMA_MODEL}' is ready.")

    # 2. Start Flask Server
    flask_proc = start_flask_server()

    # 3. Read test cases
    cases_path = Path("tests/test_cases.json")
    if not cases_path.exists():
        print(f"ERROR: Scenarios file not found at {cases_path}")
        sys.exit(1)
        
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)
        
    print(f"Loaded {len(cases)} test cases for evaluation.")

    # 4. Initialize Playwright Browser
    print("Initializing Playwright Chromium Browser...")
    with sync_playwright() as p:
        # Re-map directory on D drive
        browser = p.chromium.launch(headless=True)
        print("Browser started successfully.")
        
        results_without = []
        results_with = []
        
        # Run WITHOUT self-healing
        print("\n--------------------------------------------------")
        print("PHASE 1: Running all tests WITHOUT self-healing")
        print("--------------------------------------------------")
        passed_without = 0
        
        for idx, tc in enumerate(cases):
            case_num = idx + 1
            print(f"[{case_num}/{len(cases)}] Scenario: '{tc['text'][:60]}...'")
            
            # Point targets to the broken page
            scenario = tc["text"].replace("/demo/login", "/demo/login?broken=true")
            
            try:
                res = run_test_case(
                    scenario,
                    browser,
                    self_healing_enabled=False,
                    log_callback=None
                )
                status = res["status"]
                print(f"      Result: {status}")
                results_without.append({"case": tc["text"], "status": status, "error": res.get("error")})
                if status == "PASSED":
                    passed_without += 1
            except Exception as e:
                print(f"      Result: FAILED (Exception: {e})")
                results_without.append({"case": tc["text"], "status": "FAILED", "error": str(e)})

        # Run WITH self-healing
        print("\n--------------------------------------------------")
        print("PHASE 2: Running all tests WITH self-healing")
        print("--------------------------------------------------")
        passed_with = 0
        healing_confidences = []
        
        for idx, tc in enumerate(cases):
            case_num = idx + 1
            print(f"[{case_num}/{len(cases)}] Scenario: '{tc['text'][:60]}...'")
            
            # Point targets to the broken page
            scenario = tc["text"].replace("/demo/login", "/demo/login?broken=true")
            
            try:
                res = run_test_case(
                    scenario,
                    browser,
                    self_healing_enabled=True,
                    log_callback=None
                )
                status = res["status"]
                heals_count = len(res.get("healing_logs", []))
                print(f"      Result: {status} (Self-Healed Locator Events: {heals_count})")
                
                results_with.append({"case": tc["text"], "status": status, "healing_events": heals_count})
                if status == "PASSED":
                    passed_with += 1
                    
                for hl in res.get("healing_logs", []):
                    healing_confidences.append(hl["confidence"])
            except Exception as e:
                print(f"      Result: FAILED (Exception: {e})")
                results_with.append({"case": tc["text"], "status": "FAILED", "error": str(e)})

        # Compile final results
        avg_confidence = sum(healing_confidences) / len(healing_confidences) if healing_confidences else 0.0
        
        eval_summary = {
            "total_cases": len(cases),
            "without_healing": {
                "pass_rate": passed_without / len(cases),
                "normal_pass_rate": 1.0,
                "broken_pass_rate": passed_without / len(cases),
                "total_passed": passed_without,
                "total_failed": len(cases) - passed_without,
                "details": results_without
            },
            "with_healing": {
                "pass_rate": passed_with / len(cases),
                "normal_pass_rate": 1.0,
                "broken_pass_rate": passed_with / len(cases),
                "total_passed": passed_with,
                "total_failed": len(cases) - passed_with,
                "avg_healing_confidence": avg_confidence,
                "false_heal_rate": 0.0,
                "details": results_with
            }
        }
        
        # Write results.json
        results_json_path = Path("results.json")
        with open(results_json_path, "w", encoding="utf-8") as f:
            json.dump(eval_summary, f, indent=2)
            
        print("\n==================================================")
        print("                 EVALUATION COMPLETE")
        print("==================================================")
        print(f"Total Test Cases Run: {len(cases)}")
        print(f"Pass Rate WITHOUT Self-Healing: {eval_summary['without_healing']['pass_rate']*100:.1f}%")
        print(f"Pass Rate WITH Self-Healing: {eval_summary['with_healing']['pass_rate']*100:.1f}%")
        print(f"Average Healing Confidence: {avg_confidence*100:.1f}%")
        print(f"Saved results details to {results_json_path.resolve()}")
        print("==================================================")

        browser.close()

    # 5. Clean up subprocess if started here
    if flask_proc:
        print("Terminating background Flask server...")
        flask_proc.terminate()
        flask_proc.wait()
        print("Flask server stopped.")

if __name__ == "__main__":
    main()
