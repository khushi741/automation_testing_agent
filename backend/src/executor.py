import re
import logging
from typing import Any
from src.parser import TestStep
from src.config import PLAYWRIGHT_TIMEOUT

logger = logging.getLogger(__name__)

def resolve_locator(page, target: str, action: str):
    """
    Attempts to resolve target description to a Playwright locator.
    Prefers standard IDs, names, placeholders, and roles over arbitrary strings.
    """
    # If the target is already a resolved CSS selector or XPath (resulting from healing)
    if any(target.startswith(c) for c in ['#', '.', '[', '//']) or 'xpath=' in target:
        return page.locator(target)

    target_lower = target.lower()

    # 1. Username input matching
    if "username" in target_lower or "usr" in target_lower or "user" in target_lower:
        return page.locator('input#username, input[name="username"], input[placeholder*="Username" i], #username, [name="username"]')

    # 2. Password input matching
    if "password" in target_lower or "pass" in target_lower:
        return page.locator('input#password, input[name="password"], input[type="password"], #password, [name="password"]')

    # 3. Action is a click and target is button/link related
    if action == "click":
        if any(keyword in target_lower for keyword in ["button", "btn", "submit", "login", "sign"]):
            return page.locator('button[type="submit"], input[type="submit"], button#login-btn, #login-btn, button:has-text("Login"), button:has-text("Sign in")')
        if "link" in target_lower or "anchor" in target_lower:
            clean_name = target.replace("link", "").replace("anchor", "").strip()
            return page.get_by_role("link", name=clean_name or target, exact=False)

    # 4. Welcome or greeting target
    if "greeting" in target_lower or "welcome" in target_lower:
        return page.locator('#welcome-message, #user-greeting, h1, h2, [id*="greeting"], [id*="welcome"]')

    # 5. Clean fallback locator
    clean_target = target.replace('"', '\\"')
    return page.locator(f'[placeholder*="{clean_target}" i], [aria-label*="{clean_target}" i], :has-text("{clean_target}")')

def execute_step(page, step: TestStep, timeout: int = PLAYWRIGHT_TIMEOUT) -> bool:
    """
    Executes a single TestStep on the provided page.
    Raises Playwright errors or AssertErrors on failure.
    """
    action = step.action
    target = step.target
    value = step.value
    
    logger.info(f"Executing: {step.description} (Action: {action}, Target: {target}, Value: {value})")

    if action == "navigate":
        # Navigating is always successful if it completes without throwing
        page.goto(target, timeout=timeout)
        page.wait_for_load_state("networkidle", timeout=timeout)
        return True

    elif action == "click":
        locator = resolve_locator(page, target, action)
        locator.click(timeout=timeout)
        return True

    elif action == "type":
        locator = resolve_locator(page, target, action)
        locator.fill(value or "", timeout=timeout)
        return True

    elif action == "assert_text":
        def normalize_str(s: str) -> str:
            return re.sub(r'[^\w\s]', '', s.lower()).strip()

        if target.lower() == "page":
            body_text = page.locator("body").inner_text(timeout=timeout)
            if value and (value not in body_text and normalize_str(value) not in normalize_str(body_text)):
                raise AssertionError(f"Expected page text '{value}' not found in DOM.")
        else:
            locator = resolve_locator(page, target, action)
            element_text = locator.inner_text(timeout=timeout)
            if value and (value not in element_text and normalize_str(value) not in normalize_str(element_text)):
                raise AssertionError(f"Element text target '{target}' does not contain expected value '{value}'. Found: '{element_text}'")
        return True

    elif action == "assert_visible":
        try:
            locator = resolve_locator(page, target, action)
            locator.wait_for(state="visible", timeout=timeout)
            if not locator.is_visible():
                raise AssertionError(f"Target element '{target}' is not visible on page.")
        except Exception:
            text_loc = page.get_by_text(target, exact=False)
            text_loc.wait_for(state="visible", timeout=timeout)
            if not text_loc.is_visible():
                raise AssertionError(f"Target element '{target}' is not visible on page.")
        return True

    elif action == "assert_url":
        page.wait_for_load_state("networkidle", timeout=timeout)
        current_url = page.url
        if value not in current_url:
            raise AssertionError(f"Expected URL to contain '{value}', but current URL is '{current_url}'.")
        return True

    else:
        raise ValueError(f"Unsupported step action: {action}")
