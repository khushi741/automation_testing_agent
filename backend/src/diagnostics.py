"""
Diagnostics Engine — Analyzes test case results (passed, failed, healed),
pinpoints the exact root cause, and generates actionable fixes with code suggestions
and the exact file in the repository where the fix should be applied.
"""
import re
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


from urllib.parse import urlparse

def _find_route_file(route: str, step_target: str, repo_context: Optional[dict]) -> Tuple[Optional[str], str]:
    """Finds the source code file where this route was defined in the repository."""
    if not repo_context or "routes" not in repo_context:
        return None, "GET"
        
    clean_route_path = ""
    if route:
        try:
            if "://" in route:
                clean_route_path = urlparse(route).path
            else:
                clean_route_path = route.split("?")[0]
        except Exception:
            clean_route_path = route

    clean_step_path = ""
    if step_target and "://" in step_target:
        try:
            clean_step_path = urlparse(step_target).path
        except Exception:
            clean_step_path = step_target

    for r in repo_context.get("routes", []):
        p = r.get("path", "")
        if not p:
            continue
        p_norm = p.rstrip("/") or "/"

        # Match against route or step_target
        if (
            p == route 
            or (clean_route_path and p == clean_route_path)
            or (clean_route_path and p_norm != "/" and p_norm in clean_route_path)
            or (step_target and p == step_target)
            or (clean_step_path and p == clean_step_path)
            or (clean_step_path and p_norm != "/" and p_norm in clean_step_path)
            or (step_target and p in step_target)
            or (route and p in route)
        ):
            raw_file = r.get("file")
            clean_file = raw_file.replace("\\", "/") if raw_file else None
            return clean_file, r.get("method", "GET").upper()

    # If no specific route matched, fallback to first route's file if available
    routes = repo_context.get("routes", [])
    if routes and routes[0].get("file"):
        raw_file = routes[0].get("file")
        return raw_file.replace("\\", "/"), routes[0].get("method", "GET").upper()

    return None, "GET"


def diagnose_test_case(
    test_case: Dict[str, Any],
    repo_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyzes a test case execution result and returns a comprehensive
    root-cause diagnosis, actionable fix guide, and target file recommendation.
    """
    status = (test_case.get("status") or "failed").lower()
    description = test_case.get("description") or ""
    source_route = test_case.get("source_route") or ""
    error = test_case.get("error") or ""
    steps = test_case.get("steps_json") or []
    healing_events = test_case.get("healing_events") or []

    # Find failing step if any
    failed_step = None
    for step in steps:
        if isinstance(step, dict) and step.get("status") == "FAILED":
            failed_step = step
            if not error and step.get("error"):
                error = step.get("error")
            break

    # If test passed
    if status == "passed":
        return _diagnose_passed(description, source_route, steps, repo_context)

    # If test healed
    if status == "healed" or healing_events:
        return _diagnose_healed(description, source_route, healing_events, steps, repo_context)

    # Test failed: analyze specific failure patterns
    return _diagnose_failed(description, source_route, error, failed_step, repo_context)


def _diagnose_passed(description: str, route: str, steps: list, repo_context: Optional[dict]) -> Dict[str, Any]:
    step_count = len(steps)
    source_file, _ = _find_route_file(route, "", repo_context)
    target_file = source_file or "tests/test_spec.py"

    return {
        "status": "passed",
        "title": "Route Verification Succeeded",
        "category": "Healthy Endpoint",
        "target_file": target_file,
        "root_cause": (
            f"All {step_count} execution step(s) completed successfully. "
            f"The target route '{route or 'target'}' rendered without HTTP errors, console crashes, or unhandled exceptions."
        ),
        "severity": "None",
        "fix_recommendation": (
            f"No immediate fix required! The route in `{target_file}` is functioning nominally. "
            "To harden this test case, consider adding deeper assertions (e.g. verifying specific text, form inputs, or table rows)."
        ),
        "suggested_code": (
            "# Optional assertion hardening with Playwright:\n"
            "await expect(page).toHaveTitle(/.*Dashboard.*/);\n"
            "await expect(page.locator('main')).toBeVisible();"
        ),
        "prevention_tip": "Keep routes covered under continuous integration to detect future regressions early."
    }


def _diagnose_healed(description: str, route: str, healing_events: list, steps: list, repo_context: Optional[dict]) -> Dict[str, Any]:
    healed_info = []
    for h in healing_events:
        orig = h.get("original_selector") if isinstance(h, dict) else getattr(h, "original_selector", "")
        healed = h.get("healed_selector") if isinstance(h, dict) else getattr(h, "healed_selector", "")
        conf = h.get("confidence_score") if isinstance(h, dict) else getattr(h, "confidence_score", 0.0)
        healed_info.append(f"'{orig}' -> '{healed}' ({conf * 100:.1f}% confidence)")

    healed_str = "; ".join(healed_info) if healed_info else "Original selector was replaced with a semantically matching element"
    source_file, _ = _find_route_file(route, "", repo_context)
    target_file = source_file or "templates/index.html (or tests/test_spec.py)"

    return {
        "status": "healed",
        "title": "Self-Healing Repaired Broken Selector",
        "category": "Selector Drift (Auto-Repaired)",
        "target_file": target_file,
        "root_cause": (
            f"The original element selector broke due to UI changes, but HealAgent's embedding model "
            f"successfully matched an alternative element: {healed_str}."
        ),
        "severity": "Low (Self-Healed)",
        "fix_recommendation": (
            f"Although the test passed thanks to self-healing, you should update the template or test script "
            f"in `{target_file}` with the permanent healed selector to avoid self-healing latency on every run."
        ),
        "suggested_code": (
            f"// Update selector in your UI template or test script:\n"
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

    source_file, route_method = _find_route_file(route, step_target, repo_context)

    # Case 1: Timeout navigating to route
    if "timeout" in err_lower and ("page.goto" in err_lower or step_action == "navigate"):
        if route_method == "POST":
            target_file = source_file or "main.py"
            return {
                "status": "failed",
                "title": f"HTTP Method Mismatch on {route or step_target}",
                "category": "Method & Payload Mismatch",
                "target_file": target_file,
                "root_cause": (
                    f"The test attempted browser GET navigation to '{step_target or route}', but this endpoint is registered "
                    f"as a POST route in `{target_file}`. In standard browsers, typing or navigating to a URL issues a GET request, "
                    f"which fails or times out without the expected JSON request body."
                ),
                "severity": "High",
                "fix_recommendation": (
                    f"1. Open `{target_file}` to check the payload schema expected by this POST endpoint.\n"
                    "2. If this endpoint is triggered by a UI form, update the test case to navigate to the form page and click submit.\n"
                    "3. If this is an API endpoint, test it using an API POST request with the required JSON body."
                ),
                "suggested_code": (
                    f"# Test this endpoint via Playwright API (e.g. in tests/test_api.py):\n"
                    f"response = page.request.post('{step_target or route}', data={{\"flow_id\": 1, \"features\": [0.5, 1.2]}})\n"
                    f"assert response.ok\n\n"
                    f"# Or verify via curl in your terminal:\n"
                    f"curl -X POST {step_target or route} -H 'Content-Type: application/json' -d '{{\"data\": 123}}'"
                ),
                "prevention_tip": "Tag API-only endpoints in your repository scanner so test generators construct API POST requests instead of browser page navigations."
            }
        else:
            target_file = source_file or "main.py"
            return {
                "status": "failed",
                "title": f"Server Unreachable / Navigation Timeout on {route or step_target}",
                "category": "Environment & Server Port",
                "target_file": target_file,
                "root_cause": (
                    f"The browser timed out after 3000ms trying to navigate to '{step_target or route}'. "
                    f"The target server serving `{target_file}` is either not running on this port (e.g. backend runs on 8000 while test targeted 3000), "
                    f"or the route took longer than 3 seconds to complete initial load."
                ),
                "severity": "High",
                "fix_recommendation": (
                    f"1. Start your application server defined in `{target_file}` before running tests.\n"
                    "2. Check if your backend server runs on port 8000 while the test targeted port 3000.\n"
                    "3. If the route performs heavy computation on load, increase navigation timeout from 3000ms to 10000ms."
                ),
                "suggested_code": (
                    f"# Start your application server (e.g. in terminal):\n"
                    f"uvicorn {target_file.replace('.py', '').replace('/', '.')}:app --port 8000 --reload\n\n"
                    f"# Or in Playwright test configuration:\n"
                    f"await page.goto('{step_target or route}', {{ timeout: 10000 }});"
                ),
                "prevention_tip": "Configure a dynamic BASE_URL environment variable so tests always connect to the active server port."
            }

    # Case 2: Element selector not found
    if "not found" in err_lower or "selector" in err_lower or "could not find" in err_lower or step_action in ["click", "fill", "type"]:
        target_selector = step_target or "target element"
        target_file = source_file or "templates/index.html (or components/*.tsx)"
        clean_selector = target_selector.replace("#", "").replace(".", "")
        return {
            "status": "failed",
            "title": f"Element Selector Not Found ({target_selector})",
            "category": "DOM & Selector Drift",
            "target_file": target_file,
            "root_cause": (
                f"Playwright was unable to find element '{target_selector}' on the page. "
                f"The element may not have loaded yet, its ID/class name was modified, or it resides inside an iframe/shadow DOM."
            ),
            "severity": "Medium",
            "fix_recommendation": (
                f"1. Open your UI template in `{target_file}` and verify that the element exists.\n"
                f"2. Add a resilient `data-testid=\"{clean_selector}\"` attribute to the HTML element.\n"
                "3. Ensure Self-Healing is toggled ON to let HealAgent find alternative matching elements automatically."
            ),
            "suggested_code": (
                f"<!-- Paste/update in your HTML template ({target_file}): -->\n"
                f"<button data-testid=\"{clean_selector}\" id=\"{clean_selector}\" class=\"btn-primary\">\n"
                f"  Submit\n"
                f"</button>\n\n"
                f"// In your test script (e.g. tests/e2e.spec.ts):\n"
                f"await page.locator('[data-testid=\"{clean_selector}\"]').click();"
            ),
            "prevention_tip": "Avoid coupling tests to CSS layout classes like '.btn-indigo-600' which frequently change during style updates."
        }

    # Case 3: Assertion error (text mismatch)
    if "assert" in err_lower or "expected" in err_lower or step_action == "assert":
        target_file = source_file or "templates/index.html (or tests/test_spec.py)"
        return {
            "status": "failed",
            "title": "Content Assertion Mismatch",
            "category": "Verification Assertion",
            "target_file": target_file,
            "root_cause": (
                f"The page loaded, but did not contain the expected text or condition. "
                f"Error detail: {error or 'Expected content was absent from the rendered DOM'}"
            ),
            "severity": "Medium",
            "fix_recommendation": (
                f"1. Check the rendered HTML in `{target_file}` to confirm the actual text displayed on the page.\n"
                "2. Verify whether user authentication or session cookies are required before this content appears.\n"
                "3. Check for dynamic loading states (spinners) that might delay rendering of the target text."
            ),
            "suggested_code": (
                "// In your test script (tests/test_spec.py):\n"
                "await page.waitForLoadState('networkidle');\n"
                "await expect(page.locator('body')).toContainText('Expected Content');"
            ),
            "prevention_tip": "Use case-insensitive partial match assertions rather than rigid exact string equality."
        }

    # Default fallback failure
    target_file = source_file or "tests/test_spec.py"
    return {
        "status": "failed",
        "title": "Test Execution Failed",
        "category": "Execution Error",
        "target_file": target_file,
        "root_cause": error or f"Test scenario failed during action '{step_action or 'execution'}' on '{step_target or route}'.",
        "severity": "Medium",
        "fix_recommendation": (
            f"1. Review the route implementation in `{target_file}` and the failure screenshot below.\n"
            "2. Review browser console logs to see if unhandled JavaScript exceptions occurred on the page.\n"
            "3. Re-run with self-healing enabled to determine if semantic element matching resolves the failure."
        ),
        "suggested_code": (
            "# Run Playwright in interactive debug mode:\n"
            "PWDEBUG=1 pytest tests/test_spec.py"
        ),
        "prevention_tip": "Capture failure screenshots and network traces on failure for rapid root-cause isolation."
    }
