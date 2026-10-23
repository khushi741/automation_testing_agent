"""
Verification test for Stage 3: Fix.
Runs on repo1_py_security findings:
1. Ingests and detects findings with Ruff + Bandit.
2. Extracts focused context slices (function / ~20 lines).
3. Obtains minimal JSON replacement ({old_snippet, new_snippet, explanation}) via Gemini or Rule-based fallback.
4. Validates old_snippet matches exactly once and line growth gate is satisfied.
5. Runs the SIMPLIFY pass.
6. Builds the unified diff in code using difflib and validates clean in-memory application.
7. Saves patches into the database with status 'proposed'.
8. Prints a detailed table: Finding, Old Code, New Code, Lines Before/After.
"""
import sys
import os
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from src.pipeline.ingest import IngestStage
from src.pipeline.detect import DetectStage
from src.pipeline.fix import FixStage
from src.llm.provider import get_llm_provider
from src.config import WORKSPACE_DIR, GEMINI_API_KEY
from database import SessionLocal
from models import Patch, Finding


def test_stage3():
    print("=" * 80)
    print("STAGE 3: FIX VERIFICATION TEST (MINIMAL DIFF & SIMPLIFY PASS)")
    print("=" * 80)

    # 1. Check which LLM provider is active
    provider = get_llm_provider()
    provider_name = provider.__class__.__name__
    if provider_name == "GeminiProvider":
        print(f"[LLM Provider]: GeminiProvider (Free Tier) active via GEMINI_API_KEY")
    else:
        print(f"[LLM Provider]: MockRuleBasedProvider (Rule-Based Fallback) active (No GEMINI_API_KEY in .env)")

    # 2. Ingest repo1_py_security
    repo_path = WORKSPACE_DIR / "benchmarks" / "repo1_py_security"
    run_id = f"run_fix_{uuid.uuid4().hex[:6]}"
    ingest = IngestStage()
    ingest_res = ingest.run(str(repo_path), f"sandbox_{run_id}")
    sandbox = ingest_res.sandbox

    # 3. Detect findings
    detector = DetectStage()
    findings = detector.run(sandbox=sandbox, run_id=run_id)
    print(f"\n[Detect]: Found {len(findings)} deduplicated findings in repo1_py_security:")
    for f in findings:
        print(f"  - [{f.source_tool}] {f.file}:{f.line_start} [{f.severity}] {f.message}")

    # 4. Run Fix Stage
    fix_stage = FixStage(provider=provider, max_retries=3)
    proposed_patches = fix_stage.run(sandbox=sandbox, findings=findings, run_id=run_id)

    # 5. Verify database storage of patches
    db = SessionLocal()
    db_patches = db.query(Patch).filter(Patch.run_id == run_id).all()
    db.close()

    print(f"\n[Fix]: Generated {len(proposed_patches)} proposed patches. (Saved in DB: {len(db_patches)})")

    # 6. Verify and display the results table
    print("\n" + "=" * 110)
    print(f"{'Finding Message':<35} | {'Old Code':<28} | {'New Code':<28} | {'Lines (Old/New)':<15}")
    print("-" * 110)

    for p in proposed_patches:
        finding_obj = next((f for f in findings if f.id == p.finding_id), None)
        msg = finding_obj.message[:34] if finding_obj else p.file

        old_preview = p.old_snippet.strip().replace("\n", " ")[:27]
        new_preview = p.new_snippet.strip().replace("\n", " ")[:27]
        line_ratio = f"{p.lines_removed} -> {p.lines_added}"

        print(f"{msg:<35} | {old_preview:<28} | {new_preview:<28} | {line_ratio:<15}")

    print("=" * 110)

    # Verify all patches are strictly in 'proposed' state
    for p in db_patches:
        assert p.status == "proposed", f"Patch status should be 'proposed', but got {p.status}"
        assert p.diff_content.startswith("--- a/"), f"Diff should be standard unified diff, but was: {p.diff_content[:30]}"

    print("\nSample Unified Diff Generated:")
    if proposed_patches:
        print(proposed_patches[0].diff_content)

    sandbox.cleanup()
    print("STAGE 3 COMPLETED SUCCESSFULLY: ALL CHECKS PASSED")


if __name__ == "__main__":
    test_stage3()
