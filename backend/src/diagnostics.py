"""
Diagnostics Engine — Analyzes test case results (passed, failed, healed),
pinpoints the exact root cause, and generates actionable fixes with code suggestions.
"""
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def diagnose_test_case(
    test_case: Dict[str, Any],
    repo_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyzes a test case execution result and returns a comprehensive
    root-cause diagnosis and actionable fix guide.
    """
    status = (test_case.get("status") or "failed").lower()
    description = test_case.get("description") or ""
    source_route = test_case.get("source_route") or ""
    error = test_case.get("error") or ""
    steps = test_case.get("steps_json") or []
    healing_events = test_case.get("healing_events") or []

    # Find the failing step if any
    failed_step = None
    for step in steps:
        if isinstance(step, dict) and step.get("status") == "FAILED":
            failed_step = step
            if not error and step.get("error"):
                error = step.get("error")
            break

    # If test passed
    if status == "passed":
        return _diagnose_passed(description, source_route, steps)

    # If test healed
    if status == "healed" or healing_events:
        return _diagnose_healed(description, source_route, healing_events, steps)

    # Test failed: analyze specific failure patterns
    return _diagnose_failed(description, source_route, error, failed_step, repo_context)


def _diagnose_passed(description: str, route: str, steps: list) -> Dict[str, Any]:
    step_count = len(steps)
    return {
        "status": "passed",
        "title": "Route Verification Succeeded",
        "category": "Healthy Endpoint",
        "root_cause": (
            f"All {step_count} execution step(s) completed successfully. "
            f"The target route '{route or 'target'}' rendered without HTTP errors, console crashes, or unhandled exceptions."
        ),
        "severity": "None",
        "fix_recommendation": (
            "No fix required. The route is functioning nominally. "
            "To harden this test case, consider adding deeper assertions (e.g. verifying specific text, form inputs, or table rows)."
        ),
        "suggested_code": (
            "# Optional assertion hardening with Playwright:\n"
            "await expect(page).toHaveTitle(/.*Dashboard.*/);\n"
            "await expect(page.locator('main')).toBeVisible();"
        ),
        "prevention_tip": "Keep routes covered under continuous integration to detect future regressions early."
    }


def _diagnose_healed(description: str, route: str, healing_events: list, steps: list) -> Dict[str, Any]:
    healed_info = []
    for h in healing_events:
        orig = h.get("original_selector") if isinstance(h, dict) else getattr(h, "original_selector", "")
        healed = h.get("healed_selector") if isinstance(h, dict) else getattr(h, "healed_selector", "")
        conf = h.get("confidence_score") if isinstance(h, dict) else getattr(h, "confidence_score", 0.0)
        healed_info.append(f"'{orig}' -> '{healed}' ({conf * 100:.1f}% confidence)")

    healed_str = "; ".join(healed_info) if healed_info else "Original selector was replaced with a semantically matching element"

    return {
        "status": "healed",
        "title": "Self-Healing Repaired Broken Selector",
        "category": "Selector Drift (Auto-Repaired)",
        "root_cause": (
            f"The original element selector broke due to UI changes, but HealAgent's embedding model "
            f"successfully matched an alternative element: {healed_str}."
        ),
        "severity": "Low (Self-Healed)",
        "fix_recommendation": (
            "Although the test passed thanks to self-healing, you should update your test script "
            "with the healed selector to permanently prevent selector latency."
        ),
        "suggested_code": (
            f"// Update test scenario with healed selector:\n"
            f"// Replace original broken selector with the permanent locator:\n"
            f"await page.locator('{healing_events[0].get('healed_selector', '#new-selector') if healing_events and isinstance(healing_events[0], dict) else '#healed-selector'}').click();"
        ),
        "prevention_tip": "Add dedicated 'data-testid' attributes to key interactive elements to make tests immune to UI redesigns."
    }


def _diagnose_failed(
    description: str,
    route: str,
    error: str,
    failed_step: Optional[dict],
    repo_context: Optional[dict]
) -> Dict[str, Any]:
    err_lower = (error or "").lower()
    step_action = (failed_step.get("action") if failed_step else "") or ""
    step_target = (failed_step.get("target") if failed_step else "") or ""

    # Check for route method (e.g. POST route in repository)
    route_method = "GET"
    if repo_context and "routes" in repo_context:
        for r in repo_context.get("routes", []):
            if r.get("path") == route or r.get("path") == step_target:
                route_method = r.get("method", "GET").upper()
                break

    # Case 1: Timeout navigating to route
    if "timeout" in err_lower and ("page.goto" in err_lower or step_action == "navigate"):
        if route_method == "POST":
            return {
                "status": "failed",
                "title": f"HTTP Method Mismatch on {route or step_target}",
                "category": "Method & Payload Mismatch",
                "root_cause": (
                    f"The test attempted browser GET navigation to '{step_target or route}', but this route is registered "
                    f"as a POST endpoint. In browsers, direct URL navigation sends a GET request, resulting in a timeout or 405 Method Not Allowed."
                ),
                "severity": "High",
                "fix_recommendation": (
                    "1. Change the test case to submit a POST request with the required JSON body.\n"
                    "2. If this endpoint belongs to an interactive web form, navigate to the form page first and click the submit button.\n"
                    "3. For API endpoints, test via Playwright's APIRequestContext or a dedicated REST test."
                ),
                "suggested_code": (
                    f"# In Playwright Python test:\n"
                    f"response = page.request.post('{step_target or route}', data={{'key': 'value'}})\n"
                    f"assert response.ok\n\n"
                    f"# Or via curl:\n"
                    f"curl -X POST {step_target or route} -H 'Content-Type: application/json' -d '{{\"data\": 123}}'"
                ),
                "prevention_tip": "Tag API-only endpoints in your repository scanner so test generators construct API POST requests instead of browser page navigations."
            }
        else:
            return {
                "status": "failed",
                "title": f"Server Unreachable / Navigation Timeout on {route or step_target}",
                "category": "Environment & Server Port",
                "root_cause": (
                    f"The browser timed out after 3000ms trying to navigate to '{step_target or route}'. "
                    f"The target server is either not running on this port (e.g. backend runs on 8000 while test targeted 3000), "
                    f"or the route took longer than 3 seconds to complete initial load."
                ),
                "severity": "High",
                "fix_recommendation": (
                    "1. Ensure the application server is actively running before executing tests.\n"
                    "2. Check if your backend server runs on port 8000 (FastAPI default) while the test targeted port 3000.\n"
                    "3. If the route performs heavy computation on load, increase navigation timeout from 3000ms to 10000ms."
                ),
                "suggested_code": (
                    f"# Start the server on the expected port:\n"
                    f"uvicorn main:app --port 8000 --reload\n\n"
                    f"# Or in Playwright test configuration:\n"
                    f"await page.goto('{step_target or route}', {{ timeout: 10000 }});"
                ),
                "prevention_tip": "Configure a dynamic BASE_URL environment variable so tests always connect to the active server port."
            }

    # Case 2: Element selector not found
    if "not found" in err_lower or "selector" in err_lower or "could not find" in err_lower or step_action in ["click", "fill", "type"]:
        target_selector = step_target or "target element"
        return {
            "status": "failed",
            "title": f"Element Selector Not Found ({target_selector})",
            "category": "DOM & Selector Drift",
            "root_cause": (
                f"Playwright was unable to find element '{target_selector}' on the page. "
                f"The element may not have loaded yet, its ID/class name was modified, or it resides inside an iframe/shadow DOM."
            ),
            "severity": "Medium",
            "fix_recommendation": (
                "1. Verify that the element exists on the page at the time the action is performed.\n"
                "2. Ensure Self-Healing is toggled ON to let HealAgent find alternative matching elements automatically.\n"
                "3. Add explicit wait for the element (`page.wait_for_selector(...)`) or use resilient 'data-testid' selectors."
            ),
            "suggested_code": (
                f"<!-- Add resilient test ID in HTML / JSX -->\n"
                f"<button data-testid=\"action-btn\" id=\"{target_selector.replace('#', '')}\">\n"
                f"  Submit\n"
                f"</button>\n\n"
                f"// Playwright locator:\n"
                f"await page.locator('[data-testid=\"action-btn\"]').click();"
            ),
            "prevention_tip": "Avoid coupling tests to CSS layout classes like '.btn-indigo-600' which frequently change during style updates."
        }

    # Case 3: Assertion error (text mismatch)
    if "assert" in err_lower or "expected" in err_lower or step_action == "assert":
        return {
            "status": "failed",
            "title": "Content Assertion Mismatch",
            "category": "Verification Assertion",
            "root_cause": (
                f"The page loaded, but did not contain the expected text or condition. "
                f"Error detail: {error or 'Expected content was absent from the rendered DOM'}"
            ),
            "severity": "Medium",
            "fix_recommendation": (
                "1. Review the rendered HTML to check the actual text displayed on the page.\n"
                "2. Verify whether user authentication or session cookies are required before this content appears.\n"
                "3. Check for dynamic loading states (spinners) that might delay rendering of the target text."
            ),
            "suggested_code": (
                "// Wait for asynchronous content before asserting:\n"
                "await page.waitForLoadState('networkidle');\n"
                "await expect(page.locator('body')).toContainText('Expected Content');"
            ),
            "prevention_tip": "Use case-insensitive partial match assertions rather than rigid exact string equality."
        }

    # Default fallback failure
    return {
        "status": "failed",
        "title": "Test Execution Failed",
        "category": "Execution Error",
        "root_cause": error or f"Test scenario failed during action '{step_action or 'execution'}' on '{step_target or route}'.",
        "severity": "Medium",
        "fix_recommendation": (
            "1. Check the execution steps and failure screenshot below to inspect the state of the page at the moment of failure.\n"
            "2. Review browser console logs to see if unhandled JavaScript exceptions occurred on the page.\n"
            "3. Re-run with self-healing enabled to determine if semantic element matching resolves the failure."
        ),
        "suggested_code": (
            "// Run with Playwright debug mode:\n"
            "PWDEBUG=1 pytest test_spec.py"
        ),
        "prevention_tip": "Capture failure screenshots and network traces on failure for rapid root-cause isolation."
    }
