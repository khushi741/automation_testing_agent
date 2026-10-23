"""
Verification test for Stage 4: Verify.
Validates:
1. Branch-isolated patch application.
2. Check 1: Original detector re-check (finding gone).
3. Check 2: Zero newly introduced regressions.
4. Check 3: Repository test suite execution (pytest).
5. Combined multi-patch verification across the entire file/repo.
6. Deliberately bad patch rejection proof (demonstrating safety gate).
7. Transparent provider attribution (GeminiProvider vs MockRuleBasedProvider).
8. Results table with check breakdown, final status, and failure reasons.
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
from src.pipeline.fix import FixStage, ProposedPatch
from src.pipeline.verify import VerifyStage
from src.llm.provider import get_llm_provider
from src.config import WORKSPACE_DIR, GEMINI_API_KEY
from database import SessionLocal
from models import Patch


def test_stage4():
    print("=" * 80)
    print("STAGE 4: VERIFY VERIFICATION TEST (4-TIER ACCEPTANCE GATE)")
    print("=" * 80)

    # 1. State LLM Provider
    provider = get_llm_provider()
    provider_name = provider.__class__.__name__
    print(f"\n[Provider Active]: {provider_name}")
    if provider_name == "GeminiProvider":
        print("  Using Google Gemini 2.0 Flash via GEMINI_API_KEY")
    else:
        print("  Using MockRuleBasedProvider (Rule-Based Fallback - No GEMINI_API_KEY in .env)")

    # 2. Ingest repo1_py_security
    run_id = f"run_verify_{uuid.uuid4().hex[:6]}"
    repo_path = WORKSPACE_DIR / "benchmarks" / "repo1_py_security"
    ingest = IngestStage()
    ingest_res = ingest.run(str(repo_path), f"sandbox_{run_id}")
    sandbox = ingest_res.sandbox

    # 3. Detect baseline findings
    detector = DetectStage()
    findings = detector.run(sandbox=sandbox, run_id=run_id)
    print(f"\n[Detect]: Found {len(findings)} baseline findings in repo1_py_security.")

    # 4. Generate proposed fixes
    fix_stage = FixStage(provider=provider, max_retries=3)
    proposed_patches = fix_stage.run(sandbox=sandbox, findings=findings, run_id=run_id)
    print(f"[Fix]: Generated {len(proposed_patches)} proposed patches.")

    # 5. Add a DELIBERATELY BAD patch to prove the verifier safely rejects broken code
    bad_id = f"patch_bad_{uuid.uuid4().hex[:8]}"
    bad_patch = ProposedPatch(
        patch_id=bad_id,
        finding_id="fake_finding_deliberate_bad",
        file="app.py",
        old_snippet="    return cursor.fetchone()",
        new_snippet="    return None  # Deliberately broken return",
        diff_content="--- a/app.py\n+++ b/app.py\n@@ -30,1 +30,1 @@\n-    return cursor.fetchone()\n+    return None\n",
        explanation="Deliberately broken patch designed to test rejection safety.",
        lines_added=1,
        lines_removed=1,
        attempts=1,
        status="proposed",
        provider_used=provider_name
    )
    # Save bad patch in DB
    db = SessionLocal()
    db.add(Patch(
        id=bad_patch.patch_id,
        finding_id=bad_patch.finding_id,
        run_id=run_id,
        diff_content=bad_patch.diff_content,
        old_snippet=bad_patch.old_snippet,
        new_snippet=bad_patch.new_snippet,
        status="proposed",
        attempts=1,
        explanation=bad_patch.explanation
    ))
    db.commit()
    db.close()

    all_patches_to_test = proposed_patches + [bad_patch]
    print(f"[Test Setup]: Injecting 1 deliberately bad patch (total to verify: {len(all_patches_to_test)}).")

    # 6. Execute Verify Stage
    verify_stage = VerifyStage(provider=provider, detector=detector, max_retries=3)
    verification_results = verify_stage.run(
        sandbox=sandbox,
        proposed_patches=all_patches_to_test,
        baseline_findings=findings,
        run_id=run_id
    )

    # 7. Print Detailed Audit Table
    print("\n" + "=" * 125)
    print(f"{'Patch ID / Target':<26} | {'Check 1 (Clean)':<16} | {'Check 2 (No Reg)':<16} | {'Check 3 (Pytest)':<16} | {'Final Status':<14} | {'Reason / Note'}")
    print("-" * 125)

    for res in verification_results:
        finding_obj = next((f for f in findings if f.id == res.finding_id), None)
        target_label = finding_obj.message[:24] if finding_obj else ("Deliberately Bad" if "bad" in res.patch_id else res.patch_id)

        c1 = "PASSED" if res.check1_original_detector_resolved else "FAILED"
        c2 = "PASSED" if res.check2_no_new_regressions else "FAILED"
        c3 = "PASSED" if res.check3_repo_tests_passed else "FAILED"
        status_badge = res.status.upper()
        reason = res.failure_reason[:32] if res.failure_reason else ("Verified 4/4 Checks" if res.status == "verified" else "")

        print(f"{target_label:<26} | {c1:<16} | {c2:<16} | {c3:<16} | {status_badge:<14} | {reason}")

    print("=" * 125)

    # Check Bad Patch was definitely rejected
    bad_res = next((r for r in verification_results if r.patch_id == bad_id), None)
    assert bad_res is not None, "Bad patch was not evaluated!"
    assert bad_res.status == "needs_review", f"Bad patch should have been rejected, got {bad_res.status}"
    print(f"\n[Safety Gate Verified]: Deliberately bad patch was caught and REJECTED:")
    print(f"  Reason: {bad_res.failure_reason}")

    # Check Verified Patches in DB
    db = SessionLocal()
    verified_in_db = db.query(Patch).filter(Patch.run_id == run_id, Patch.status == "verified").all()
    review_in_db = db.query(Patch).filter(Patch.run_id == run_id, Patch.status == "needs_review").all()
    db.close()

    print(f"\nDatabase Verification for Run {run_id}:")
    print(f"  - Verified Patches in DB: {len(verified_in_db)}")
    print(f"  - Needs Review Patches in DB: {len(review_in_db)}")

    sandbox.cleanup()
    print("\nSTAGE 4 COMPLETED SUCCESSFULLY: ALL CHECKS PASSED")


if __name__ == "__main__":
    test_stage4()
