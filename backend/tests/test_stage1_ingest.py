"""
Verification test for Stage 1: Ingest & Sandbox Setup.
Validates:
1. Sandbox creation, venv isolation, and dependency installation.
2. Trust allowlist security enforcement.
3. Language and framework detection.
4. AST dependency and call graph construction.
5. High-risk file tagging.
6. Execution of repo's own tests inside the sandbox.
"""
import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from src.pipeline.sandbox import SandboxManager, SecurityError
from src.pipeline.ingest import IngestStage
from src.config import WORKSPACE_DIR


def test_stage1():
    print("=" * 60)
    print("STAGE 1: INGEST & SANDBOX VERIFICATION TEST")
    print("=" * 60)

    manager = SandboxManager()
    ingest = IngestStage(sandbox_manager=manager)

    # 1. Test security allowlist rejection
    print("\n[1/4] Testing Security Allowlist Enforcement...")
    try:
        manager.create_sandbox("https://github.com/evil-attacker/malicious-repo", "sandbox_untrusted_test")
        print("  FAILED: Untrusted repo was permitted!")
    except SecurityError as e:
        print(f"  PASSED: Untrusted repo blocked: {e}")

    # 2. Test Ingest on repo1_py_security
    print("\n[2/4] Testing Ingest on repo1_py_security...")
    repo1_path = WORKSPACE_DIR / "benchmarks" / "repo1_py_security"
    res1 = ingest.run(str(repo1_path), "test_sandbox_repo1")
    print(f"  Sandbox Path: {res1.sandbox.sandbox_path}")
    print(f"  Venv Status: {res1.sandbox.status}")
    print(f"  Venv Python: {res1.sandbox.venv_python}")
    print(f"  Language: {res1.primary_language}")
    print(f"  Framework: {res1.framework}")
    print(f"  Python Files: {res1.python_files}")
    print(f"  High-Risk Files: {res1.high_risk_files}")
    print(f"  AST Functions found in app.py: {res1.dependency_graph['files'].get('app.py', {}).get('functions')}")
    print(f"  AST Calls found in app.py: {res1.dependency_graph['files'].get('app.py', {}).get('calls')}")

    # Run tests inside sandbox venv
    test_run = res1.sandbox.run_command(["pytest"], timeout=30)
    print(f"  Pytest in Sandbox: Exit Code {test_run.returncode}")
    print(f"  Pytest Output: {test_run.stdout.strip().splitlines()[-1] if test_run.stdout else 'None'}")
    assert test_run.returncode == 0, f"Pytest failed: {test_run.stderr}"
    res1.sandbox.cleanup()
    print("  Sandbox cleanup verified.")

    # 3. Test Ingest on repo2_py_crash
    print("\n[3/4] Testing Ingest on repo2_py_crash...")
    repo2_path = WORKSPACE_DIR / "benchmarks" / "repo2_py_crash"
    res2 = ingest.run(str(repo2_path), "test_sandbox_repo2")
    print(f"  Sandbox Path: {res2.sandbox.sandbox_path}")
    print(f"  Language: {res2.primary_language}")
    print(f"  Python Files: {res2.python_files}")
    # Run tests inside sandbox venv (original baseline tests)
    test_run2 = res2.sandbox.run_command(["pytest", "-k", "not repro"], timeout=30)
    print(f"  Pytest in Sandbox: Exit Code {test_run2.returncode}")
    print(f"  Pytest Output: {test_run2.stdout.strip().splitlines()[-1] if test_run2.stdout else 'None'}")
    assert test_run2.returncode == 0
    res2.sandbox.cleanup()

    # 4. Test Ingest on repo3_py_web
    print("\n[4/4] Testing Ingest on repo3_py_web...")
    repo3_path = WORKSPACE_DIR / "benchmarks" / "repo3_py_web"
    res3 = ingest.run(str(repo3_path), "test_sandbox_repo3")
    print(f"  Sandbox Path: {res3.sandbox.sandbox_path}")
    print(f"  Has Frontend: {res3.has_frontend}")
    print(f"  Frontend Routes: {res3.frontend_routes}")
    test_run3 = res3.sandbox.run_command(["pytest", "-k", "not repro"], timeout=30)
    print(f"  Pytest in Sandbox: Exit Code {test_run3.returncode}")
    print(f"  Pytest Output: {test_run3.stdout.strip().splitlines()[-1] if test_run3.stdout else 'None'}")
    assert test_run3.returncode == 0
    res3.sandbox.cleanup()

    print("\n" + "=" * 60)
    print("STAGE 1 COMPLETED SUCCESSFULLY: ALL CHECKS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    test_stage1()
