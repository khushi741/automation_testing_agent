import re
import json
import logging
import requests
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from src.config import OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

class TestStep(BaseModel):
    action: str = Field(..., description="Action type: navigate, click, type, assert_text, assert_visible, assert_url")
    target: str = Field(..., description="Target locator description or URL")
    value: Optional[str] = Field(None, description="Value to input or assert (e.g. text to type, or expected value)")
    description: str = Field(..., description="Description of the step in natural language")

class TestSuite(BaseModel):
    steps: List[TestStep]

SYSTEM_PROMPT = """You are a test automation parser. Your job is to convert a natural language test case into a structured JSON sequence of browser automation steps.
You MUST output JSON ONLY. Return a JSON object containing a "steps" key with a list of steps.

Allowed actions and their schema:
1. {"action": "navigate", "target": "URL", "value": null, "description": "Short explanation"}
2. {"action": "type", "target": "target element description (e.g., 'username field')", "value": "text to type", "description": "Short explanation"}
3. {"action": "click", "target": "target element description (e.g., 'login button')", "value": null, "description": "Short explanation"}
4. {"action": "assert_text", "target": "target element description or 'page'", "value": "expected text content", "description": "Short explanation"}
5. {"action": "assert_visible", "target": "target element description", "value": null, "description": "Short explanation"}
6. {"action": "assert_url", "target": "page", "value": "expected URL or part of URL", "description": "Short explanation"}

Ensure you capture all interactions described. Do not assume or skip any steps mentioned.
Example Output Structure:
{
  "steps": [
    {
      "action": "navigate",
      "target": "http://localhost:5000/demo/login",
      "value": null,
      "description": "Navigate to login page"
    },
    {
      "action": "type",
      "target": "username input field",
      "value": "admin",
      "description": "Enter username 'admin'"
    }
  ]
}
"""

def heuristic_fallback_parser(text: str) -> List[TestStep]:
    """
    A deterministic regex/keyword parser used when Ollama is offline or unavailable.
    Accurately maps common natural language testing phrasings to Pydantic step models.
    """
    logger.warning("Using heuristic rule-based fallback parser (Ollama is offline).")
    steps = []
    
    # Split text into logical segments by commas, semicolons, or "and", respecting quotes
    pattern = r'''(?:,\s*|;\s*|\s+\band\b\s+)(?=(?:[^'"]*['"][^'"]*['"])*[^'"]*$)'''
    clauses = [c.strip() for c in re.split(pattern, text) if c.strip()]
    for clause in clauses:
            
        clause_lower = clause.lower()
        
        # 1. Navigation
        if "navigate to" in clause_lower or "open" in clause_lower or "go to" in clause_lower:
            url_match = re.search(r'https?://[^\s]+', clause_lower)
            if url_match:
                url = url_match.group(0).rstrip('.')
                steps.append(TestStep(
                    action="navigate",
                    target=url,
                    value=None,
                    description=f"Navigate to {url}"
                ))
                
        # 1.5. Special login compound phrasings
        elif any(kw in clause_lower for kw in ["log in with", "login using", "sign in with"]):
            vals = re.findall(r"['\"]([^'\"]+)['\"]", clause)
            username = "admin"
            password = "admin123"
            if len(vals) >= 2:
                username = vals[0]
                password = vals[1]
            else:
                slash_match = re.search(r"([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)", clause)
                if slash_match:
                    username = slash_match.group(1)
                    password = slash_match.group(2)
            
            steps.append(TestStep(
                action="type",
                target="username field",
                value=username,
                description=f"Type username '{username}'"
            ))
            steps.append(TestStep(
                action="type",
                target="password field",
                value=password,
                description=f"Type password '{password}'"
            ))
            steps.append(TestStep(
                action="click",
                target="login button",
                value=None,
                description="Click login button"
            ))

        # 2. Type/Fill Text Input
        elif "type" in clause_lower or "enter" in clause_lower or "fill" in clause_lower or "write" in clause_lower:
            val_match = re.search(r"['\"]([^'\"]+)['\"]", clause)
            val = val_match.group(1) if val_match else ""
            
            field = "input field"
            if "username" in clause_lower:
                field = "username field"
            elif "password" in clause_lower:
                field = "password field"
            elif "email" in clause_lower:
                field = "email field"
            elif "account" in clause_lower:
                field = "account field"
            elif "code" in clause_lower:
                field = "security code field"
            elif "user" in clause_lower:
                field = "user input field"
            elif "pass" in clause_lower:
                field = "pass input field"
                
            steps.append(TestStep(
                action="type",
                target=field,
                value=val,
                description=f"Type '{val}' into {field}"
            ))
            
        # 3. Clicks
        elif "click" in clause_lower or "press" in clause_lower or "submit" in clause_lower:
            btn = "button"
            if "login" in clause_lower or "sign in" in clause_lower:
                btn = "login button"
            elif "logout" in clause_lower or "sign out" in clause_lower or "exit" in clause_lower:
                btn = "logout link"
            else:
                btn_match = re.search(r"['\"]([^'\"]+)['\"]", clause)
                if btn_match:
                    btn = btn_match.group(1)
                else:
                    # Capture descriptive text after click/press
                    words = clause.split()
                    for word in ["click", "press", "button", "the"]:
                        if word in words:
                            words.remove(word)
                    btn = " ".join(words).strip()
                    
            steps.append(TestStep(
                action="click",
                target=btn,
                value=None,
                description=f"Click {btn}"
            ))
            
        # 4. Assertions (Text / Visibility / URL)
        elif any(kw in clause_lower for kw in ["verify", "assert", "check", "confirm", "contains", "greeting", "welcome"]):
            val_match = re.search(r"['\"]([^'\"]+)['\"]", clause)
            val = val_match.group(1) if val_match else ""
            
            target = "page"
            if "greeting" in clause_lower or "welcome" in clause_lower:
                target = "welcome greeting"
            elif "logout" in clause_lower or "exit" in clause_lower:
                target = "logout button"
            elif "url" in clause_lower:
                target = "page"
                
            if "url" in clause_lower:
                steps.append(TestStep(
                    action="assert_url",
                    target="page",
                    value=val if val else "dashboard",
                    description=f"Verify URL contains '{val if val else 'dashboard'}'"
                ))
            else:
                action = "assert_text" if val else "assert_visible"
                steps.append(TestStep(
                    action=action,
                    target=target,
                    value=val if val else None,
                    description=f"Verify {target} displays '{val}'" if val else f"Verify {target} is visible"
                ))
                
    return steps

_OLLAMA_AVAILABLE = None

def is_ollama_available() -> bool:
    global _OLLAMA_AVAILABLE
    if _OLLAMA_AVAILABLE is False:
        return False
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=0.8)
        _OLLAMA_AVAILABLE = (r.status_code == 200)
        return _OLLAMA_AVAILABLE
    except Exception:
        _OLLAMA_AVAILABLE = False
        return False

def parse_test_case_with_llm(test_case_text: str) -> List[TestStep]:
    """
    Sends the natural language test case to local Ollama and parses the JSON output.
    Falls back to heuristic parsing if Ollama is offline.
    """
    if not is_ollama_available():
        return heuristic_fallback_parser(test_case_text)

    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this test case: {test_case_text}"}
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=2)
        response.raise_for_status()
        result_json = response.json()
        content = result_json.get("message", {}).get("content", "")
        
        # Load and parse content
        parsed_data = json.loads(content)
        
        if isinstance(parsed_data, list):
            steps_list = parsed_data
        elif isinstance(parsed_data, dict):
            if "steps" in parsed_data:
                steps_list = parsed_data["steps"]
            else:
                lists = [v for v in parsed_data.values() if isinstance(v, list)]
                if lists:
                    steps_list = lists[0]
                else:
                    steps_list = [parsed_data]
        else:
            raise ValueError(f"Invalid JSON format: {content}")

        validated_steps = []
        for step in steps_list:
            validated_steps.append(TestStep(**step))
        
        return validated_steps

    except Exception as e:
        logger.warning(f"Ollama parsing connection failed or timed out: {e}. Activating heuristic fallback...")
        return heuristic_fallback_parser(test_case_text)
