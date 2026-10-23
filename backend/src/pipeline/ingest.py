"""
Ingest Stage for HealAgent 2.0.
Responsible for:
1. Sandboxed ingestion (cloning or copying into an isolated directory).
2. Detecting project languages and frameworks.
3. Parsing Python AST to construct an import and symbol call graph.
4. Flagging high-risk files (auth, payments, db, input sanitization) for downstream scrutiny.
5. Detecting whether frontend routes/templates exist to determine if Playwright checks are required.
"""
import os
import ast
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set, Any, Optional

from src.pipeline.sandbox import SandboxManager, SandboxEnvironment

logger = logging.getLogger(__name__)

HIGH_RISK_KEYWORDS = {
    "auth", "login", "password", "token", "jwt", "session",
    "payment", "checkout", "billing", "credit",
    "db", "database", "sql", "query", "orm",
    "sanitize", "upload", "secret", "crypto", "permission"
}


@dataclass
class IngestResult:
    """Output data contract from the Ingest stage."""
    sandbox: SandboxEnvironment
    primary_language: str
    framework: str
    all_files: List[str]
    python_files: List[str]
    high_risk_files: List[str]
    dependency_graph: Dict[str, Any]
    frontend_routes: List[str] = field(default_factory=list)
    has_frontend: bool = False
    status: str = "completed"
    error_message: Optional[str] = None


class ASTDependencyVisitor(ast.NodeVisitor):
    """AST Visitor that extracts imports, function definitions, class definitions, and calls."""

    def __init__(self):
        self.imports: List[str] = []
        self.functions: List[str] = []
        self.classes: List[str] = []
        self.calls: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            self.imports.append(f"{mod}.{alias.name}" if mod else alias.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.append(node.func.attr)
        self.generic_visit(node)


class IngestStage:
    """Executes the Ingest pipeline stage."""

    def __init__(self, sandbox_manager: Optional[SandboxManager] = None):
        self.sandbox_manager = sandbox_manager or SandboxManager()

    def run(self, repo_source: str, analysis_id: str) -> IngestResult:
        logger.info(f"Starting IngestStage for '{repo_source}' (id: {analysis_id})")

        # Step 0: Tamper-evident benchmark hash integrity gate
        if "benchmarks" in str(repo_source) and not str(repo_source).endswith("oss_real_files"):
            from src.pipeline.freeze_benchmark import validate_benchmark_integrity
            ok, msg = validate_benchmark_integrity()
            if not ok:
                logger.error(f"Benchmark integrity violation: {msg}")
                raise RuntimeError(f"PIPELINE ABORTED - BENCHMARK INTEGRITY VIOLATION: {msg}")
            logger.info(f"Benchmark hash integrity verified (tamper-evident): {msg}")

        # Step 1: Create isolated sandbox and virtual environment
        sandbox = self.sandbox_manager.create_sandbox(
            repo_source=repo_source,
            sandbox_id=analysis_id,
            install_dependencies=True
        )

        root = sandbox.sandbox_path

        # Step 2: Catalog files and detect primary language
        all_files: List[str] = []
        py_files: List[str] = []
        js_files: List[str] = []

        for p in root.rglob("*"):
            if p.is_file():
                rel = str(p.relative_to(root)).replace("\\", "/")
                # Ignore internal sandbox or git dirs
                if any(ignored in rel for ignored in [".sandbox_venv", ".git", "__pycache__", "node_modules"]):
                    continue
                all_files.append(rel)
                if rel.endswith(".py"):
                    py_files.append(rel)
                elif rel.endswith((".js", ".jsx", ".ts", ".tsx")):
                    js_files.append(rel)

        primary_language = "python" if len(py_files) >= len(js_files) else "javascript"

        # Step 3: Detect Framework
        framework = self._detect_framework(root, py_files)

        # Step 4: Build AST Dependency Graph
        dep_graph: Dict[str, Any] = {
            "files": {},
            "call_map": {},
            "high_risk_files": []
        }
        high_risk_files: List[str] = []

        for rel_path in py_files:
            abs_path = root / rel_path
            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
                parsed_ast = ast.parse(content, filename=rel_path)
                visitor = ASTDependencyVisitor()
                visitor.visit(parsed_ast)

                dep_graph["files"][rel_path] = {
                    "imports": visitor.imports,
                    "functions": visitor.functions,
                    "classes": visitor.classes,
                    "calls": list(set(visitor.calls))
                }

                # High risk identification
                rel_lower = rel_path.lower()
                content_lower = content.lower()
                is_high_risk = any(kw in rel_lower for kw in HIGH_RISK_KEYWORDS) or any(
                    kw in content_lower and ("def " in content or "class " in content)
                    for kw in ["execute(", "password", "secret_key", "authorization"]
                )
                if is_high_risk:
                    high_risk_files.append(rel_path)

            except Exception as e:
                logger.warning(f"Could not parse AST for {rel_path}: {e}")
                dep_graph["files"][rel_path] = {
                    "error": str(e),
                    "imports": [],
                    "functions": [],
                    "classes": [],
                    "calls": []
                }

        dep_graph["high_risk_files"] = high_risk_files

        # Step 5: Check frontend routes / templates for optional Playwright execution
        frontend_routes = self._extract_routes(root, py_files)
        has_frontend = bool(frontend_routes or any("template" in f or "static" in f for f in all_files))

        return IngestResult(
            sandbox=sandbox,
            primary_language=primary_language,
            framework=framework,
            all_files=all_files,
            python_files=py_files,
            high_risk_files=high_risk_files,
            dependency_graph=dep_graph,
            frontend_routes=frontend_routes,
            has_frontend=has_frontend,
            status="completed"
        )

    def _detect_framework(self, root: Path, py_files: List[str]) -> str:
        req_txt = root / "requirements.txt"
        if req_txt.exists():
            try:
                content = req_txt.read_text(encoding="utf-8", errors="replace").lower()
                if "fastapi" in content:
                    return "fastapi"
                if "flask" in content:
                    return "flask"
                if "django" in content:
                    return "django"
            except Exception:
                pass

        for rel in py_files:
            abs_p = root / rel
            try:
                code = abs_p.read_text(encoding="utf-8", errors="replace").lower()
                if "import flask" in code or "from flask" in code:
                    return "flask"
                if "import fastapi" in code or "from fastapi" in code:
                    return "fastapi"
                if "import django" in code or "from django" in code:
                    return "django"
            except Exception:
                pass

        return "python_standalone"

    def _extract_routes(self, root: Path, py_files: List[str]) -> List[str]:
        routes = []
        for rel in py_files:
            abs_p = root / rel
            try:
                code = abs_p.read_text(encoding="utf-8", errors="replace")
                import re
                found = re.findall(r'@(?:app|router)\.(?:get|post|put|delete|route)\s*\(\s*["\']([^"\']+)["\']', code)
                routes.extend(found)
            except Exception:
                pass
        return list(set(routes))
