import logging
from typing import Any
from src.parser import TestStep
from src.config import PLAYWRIGHT_TIMEOUT

logger = logging.getLogger(__name__)

def resolve_locator(page, target: str, action: str):
    """
    Attempts to resolve target description to a Playwright locator.
    Prefers accessible locators (role, placeholder, label, text) over CSS.
    Falls back to CSS/XPath if target pattern matches selectors.
    """
    # If the target is already a resolved CSS selector or XPath (often resulting from healing)
    if any(target.startswith(c) for c in ['#', '.', '[', '//']) or 'xpath=' in target:
        return page.locator(target)

    target_lower = target.lower()

    # 1. Action is a click and target is button/link related
    if action == "click":
        if any(keyword in target_lower for keyword in ["button", "btn", "submit", "login", "sign"]):
            # Clean keywords to find the name
            clean_name = target
            for kw in ["button", "btn", "submit", "field", "input"]:
                clean_name = clean_name.replace(kw, "")
            clean_name = clean_name.strip()
            
            if clean_name:
                return page.get_by_role("button", name=clean_name, exact=False)
            return page.get_by_role("button", name=target, exact=False)
        
        if "link" in target_lower or "anchor" in target_lower:
            clean_name = target.replace("link", "").replace("anchor", "").strip()
            if clean_name:
                return page.get_by_role("link", name=clean_name, exact=False)
            return page.get_by_role("link", name=target, exact=False)

    # 2. Action is type/fill and target is an input field
    if action == "type" or any(keyword in target_lower for keyword in ["input", "field", "textbox", "username", "password", "email"]):
        # Extract name to match placeholder or label
        clean_name = target
        for kw in ["input", "field", "textbox", "username", "password"]:
            clean_name = clean_name.replace(kw, "")
        clean_name = clean_name.strip()
        
        # Try placeholder first
        try:
            return page.get_by_placeholder(clean_name or target, exact=False)
        except Exception:
            pass
            
        # Try label next
        try:
            return page.get_by_label(clean_name or target, exact=False)
        except Exception:
            pass

    # 3. Default to text-based matching
    return page.get_by_text(target, exact=False)

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
        if target.lower() == "page":
            # Assert text exists anywhere in the body content
            body_text = page.locator("body").inner_text(timeout=timeout)
            if value not in body_text:
                raise AssertionError(f"Expected page text '{value}' not found in DOM.")
        else:
            locator = resolve_locator(page, target, action)
            element_text = locator.inner_text(timeout=timeout)
            if value not in element_text:
                raise AssertionError(f"Element text target '{target}' does not contain expected value '{value}'. Found: '{element_text}'")
        return True

    elif action == "assert_visible":
        locator = resolve_locator(page, target, action)
        # Playwright wait_for ensures visibility check
        locator.wait_for(state="visible", timeout=timeout)
        if not locator.is_visible():
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
