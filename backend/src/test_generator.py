"""
Test Generator — uses a local LLM (or heuristic fallback) to generate
natural language test case descriptions from detected routes.
"""
import re
import json
import logging
from typing import List, Dict, Any

import requests

from src.config import OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


def generate_tests_for_routes(
    routes: List[Dict[str, str]],
    framework: str,
    base_url: str = "http://localhost:3000"
) -> List[Dict[str, str]]:
    """
    Generates natural language test case descriptions for a list of routes.
    Tries the local LLM first, falls back to heuristic generation.
    """
    all_cases = []
    use_llm = False
    try:
        from src.parser import is_ollama_available
        use_llm = is_ollama_available()
    except Exception:
        pass

    for route in routes:
        if use_llm:
            try:
                cases = _generate_with_llm(route, framework, base_url)
                if cases:
                    all_cases.extend(cases)
                    continue
            except Exception as e:
                logger.warning(f"LLM test generation failed for {route['path']}: {e}")

        # Fallback: heuristic generation
        cases = _generate_heuristic(route, framework, base_url)
        all_cases.extend(cases)

    logger.info(f"Generated {len(all_cases)} test cases for {len(routes)} routes")
    return all_cases


def _generate_with_llm(
    route: Dict[str, str], framework: str, base_url: str
) -> List[Dict[str, str]]:
    """Asks the local Ollama model to generate test cases for a route."""
    prompt = f"""You are a QA test engineer. Generate 2-3 natural language browser test case descriptions
for the following web application route.

Framework: {framework}
Route path: {route['path']}
HTTP method: {route['method']}
Source file: {route.get('file', 'unknown')}
Base URL: {base_url}

Each test case should be a single sentence describing user actions and expected outcomes.
Focus on: navigation, form inputs, button clicks, and visible content assertions.

Output ONLY a JSON array of objects with "description" and "source_route" keys.
Example: [{{"description": "Navigate to {base_url}{route['path']} and verify the page loads successfully", "source_route": "{route['path']}"}}]
"""

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json"
            },
            timeout=30
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]

        # Try to extract JSON array
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            cases = json.loads(json_match.group())
            return [
                {"description": c["description"], "source_route": c.get("source_route", route["path"])}
                for c in cases
                if isinstance(c, dict) and "description" in c
            ]
    except requests.ConnectionError:
        logger.info("Ollama not available, falling back to heuristic generation")
    except Exception as e:
        logger.warning(f"LLM generation error: {e}")

    return []


def _generate_heuristic(
    route: Dict[str, str], framework: str, base_url: str
) -> List[Dict[str, str]]:
    """
    Rule-based fallback: generates simple test cases from route metadata.
    """
    path = route["path"]
    full_url = f"{base_url}{path}"
    cases = []

    # Always generate a navigation test
    cases.append({
        "description": f"Navigate to {full_url} and verify the page loads without errors",
        "source_route": path
    })

    path_lower = path.lower()

    # Login page heuristics
    if "login" in path_lower or "signin" in path_lower or "auth" in path_lower:
        cases.append({
            "description": f"Go to {full_url}, type 'testuser' in the username field, type 'password123' in the password field, and click the login button",
            "source_route": path
        })
        cases.append({
            "description": f"Navigate to {full_url} and verify a login form with username and password fields is visible",
            "source_route": path
        })

    # Dashboard/home
    elif "dashboard" in path_lower or path == "/":
        cases.append({
            "description": f"Open {full_url} and verify the page contains a heading or welcome message",
            "source_route": path
        })

    # Settings/profile pages
    elif "settings" in path_lower or "profile" in path_lower:
        cases.append({
            "description": f"Navigate to {full_url} and verify settings or profile form elements are visible",
            "source_route": path
        })

    # Register/signup
    elif "register" in path_lower or "signup" in path_lower:
        cases.append({
            "description": f"Go to {full_url} and verify a registration form with email and password inputs is visible",
            "source_route": path
        })

    return cases
