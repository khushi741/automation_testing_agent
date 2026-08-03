"""
Repository Analyzer — clones a GitHub repository, detects the web framework,
and extracts route definitions for automated test generation.
"""
import os
import re
import json
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.config import SCRATCH_DIR

logger = logging.getLogger(__name__)


def clone_repo(github_url: str, repo_id: str) -> str:
    """
    Clones a GitHub repository into the scratch directory.
    Returns the local path of the cloned repo.
    """
    dest = SCRATCH_DIR / repo_id
    if dest.exists():
        shutil.rmtree(dest)

    logger.info(f"Cloning {github_url} into {dest}...")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", github_url, str(dest)],
        capture_output=True, text=True, timeout=120
    )

    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr.strip()}")

    logger.info(f"Repository cloned successfully to {dest}")
    return str(dest)


def detect_framework(repo_path: str) -> str:
    """
    Inspects the cloned repository to detect the primary web framework.
    Returns one of: 'nextjs', 'react', 'vue', 'flask', 'django', 'express', 'unknown'
    """
    root = Path(repo_path)

    # Check package.json for JS frameworks
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                pkg = json.load(f)
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "next" in deps:
                return "nextjs"
            elif "vue" in deps or "@vue/cli-service" in deps:
                return "vue"
            elif "react" in deps or "react-dom" in deps:
                return "react"
            elif "express" in deps:
                return "express"
        except Exception as e:
            logger.warning(f"Failed to parse package.json: {e}")

    # Check for Python frameworks
    req_txt = root / "requirements.txt"
    py_files = list(root.rglob("*.py"))

    if req_txt.exists():
        try:
            content = req_txt.read_text(encoding="utf-8").lower()
            if "flask" in content:
                return "flask"
            elif "django" in content:
                return "django"
            elif "fastapi" in content:
                return "fastapi"
        except Exception:
            pass

    # Scan Python files for framework imports
    for py_file in py_files[:20]:  # Limit scan to first 20 files
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            if "from flask" in text or "import flask" in text.lower():
                return "flask"
            elif "from django" in text:
                return "django"
            elif "from fastapi" in text:
                return "fastapi"
        except Exception:
            continue

    return "unknown"


def extract_routes(repo_path: str, framework: str) -> List[Dict[str, str]]:
    """
    Extracts route definitions from the repository based on the detected framework.
    Returns a list of dicts with 'path', 'method', and 'file' keys.
    """
    root = Path(repo_path)
    routes = []

    if framework == "nextjs":
        routes = _extract_nextjs_routes(root)
    elif framework in ("react", "vue"):
        routes = _extract_spa_routes(root, framework)
    elif framework in ("flask", "fastapi"):
        routes = _extract_python_routes(root, framework)
    elif framework == "express":
        routes = _extract_express_routes(root)
    elif framework == "django":
        routes = _extract_django_routes(root)

    # Deduplicate
    seen = set()
    unique_routes = []
    for r in routes:
        key = f"{r['method']}:{r['path']}"
        if key not in seen:
            seen.add(key)
            unique_routes.append(r)

    logger.info(f"Extracted {len(unique_routes)} routes from {framework} project")
    return unique_routes


def _extract_nextjs_routes(root: Path) -> List[Dict[str, str]]:
    """Extract routes from Next.js pages/ or app/ directory."""
    routes = []

    # Pages Router
    pages_dir = root / "pages"
    if not pages_dir.exists():
        pages_dir = root / "src" / "pages"

    if pages_dir.exists():
        for f in pages_dir.rglob("*"):
            if f.is_file() and f.suffix in (".tsx", ".ts", ".jsx", ".js"):
                rel = f.relative_to(pages_dir)
                route = "/" + str(rel).replace("\\", "/")
                # Clean up file extensions and index
                route = re.sub(r"\.(tsx|ts|jsx|js)$", "", route)
                route = re.sub(r"/index$", "", route) or "/"
                # Skip API routes and _app/_document
                if route.startswith("/api") or "/_" in route:
                    continue
                routes.append({"path": route, "method": "GET", "file": str(rel)})

    # App Router
    app_dir = root / "app"
    if not app_dir.exists():
        app_dir = root / "src" / "app"

    if app_dir.exists():
        for f in app_dir.rglob("page.*"):
            if f.suffix in (".tsx", ".ts", ".jsx", ".js"):
                rel = f.parent.relative_to(app_dir)
                route = "/" + str(rel).replace("\\", "/")
                if route == "/.":
                    route = "/"
                routes.append({"path": route, "method": "GET", "file": str(rel / f.name)})

    return routes


def _extract_spa_routes(root: Path, framework: str) -> List[Dict[str, str]]:
    """Extract routes from React Router or Vue Router config."""
    routes = []
    src_dir = root / "src"
    if not src_dir.exists():
        src_dir = root

    for f in src_dir.rglob("*"):
        if f.is_file() and f.suffix in (".tsx", ".ts", ".jsx", ".js"):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                # Match React Router path attributes or Vue Router path properties
                path_matches = re.findall(r'path\s*[:=]\s*["\']([^"\']+)["\']', text)
                for p in path_matches:
                    if p.startswith("/"):
                        routes.append({
                            "path": p,
                            "method": "GET",
                            "file": str(f.relative_to(root))
                        })
            except Exception:
                continue

    return routes


def _extract_python_routes(root: Path, framework: str) -> List[Dict[str, str]]:
    """Extract routes from Flask @app.route or FastAPI @app.get/post decorators."""
    routes = []
    pattern = re.compile(
        r'@\w+\.(route|get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
        re.IGNORECASE
    )

    for f in root.rglob("*.py"):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for match in pattern.finditer(text):
                method_hint = match.group(1).upper()
                if method_hint == "ROUTE":
                    method_hint = "GET"
                routes.append({
                    "path": match.group(2),
                    "method": method_hint,
                    "file": str(f.relative_to(root))
                })
        except Exception:
            continue

    return routes


def _extract_express_routes(root: Path) -> List[Dict[str, str]]:
    """Extract routes from Express.js app.get/post/etc. calls."""
    routes = []
    pattern = re.compile(
        r'\.\s*(get|post|put|delete|patch|all)\s*\(\s*["\']([^"\']+)["\']',
        re.IGNORECASE
    )

    for f in root.rglob("*.js"):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for match in pattern.finditer(text):
                routes.append({
                    "path": match.group(2),
                    "method": match.group(1).upper(),
                    "file": str(f.relative_to(root))
                })
        except Exception:
            continue

    return routes


def _extract_django_routes(root: Path) -> List[Dict[str, str]]:
    """Extract routes from Django urlpatterns."""
    routes = []
    pattern = re.compile(r'path\s*\(\s*["\']([^"\']*)["\']', re.IGNORECASE)

    for f in root.rglob("urls.py"):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for match in pattern.finditer(text):
                routes.append({
                    "path": "/" + match.group(1),
                    "method": "GET",
                    "file": str(f.relative_to(root))
                })
        except Exception:
            continue

    return routes


def analyze_repo(repo_path: str) -> Dict[str, Any]:
    """
    Full analysis pipeline: detect framework, extract routes.
    Returns a summary dict.
    """
    framework = detect_framework(repo_path)
    routes = extract_routes(repo_path, framework)

    return {
        "framework": framework,
        "routes": routes,
        "total_routes": len(routes)
    }
