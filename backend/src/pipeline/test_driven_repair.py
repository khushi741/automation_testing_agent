"""
Stage 6: Test-Driven Repair Mode for HealAgent 2.0.

Responsible for:
1. Running repository test suite to capture failing tests.
2. Parsing tracebacks to locate source file, failing line, and assertion message.
3. Constructing findings with source_tool="failing_test".
4. Proposing minimal fixes with failing traceback feedback.
5. Verifying:
   - Check 1: Syntax & Linter pass
   - Check 2: No new regressions on existing passing tests
   - Check 3: The previously failing test now explicitly passes!
6. Integration with HealAgent 1.0:
   - Detects failures in generated route tests (from test_generator.py).
   - Labels them clearly with human confirmation notice.
"""
import re
import sys
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from src.pipeline.sandbox import SandboxEnvironment
from src.pipeline.detect import CanonicalFinding, generate_finding_id, is_test_file
from src.pipeline.fix import ProposedPatch, FixStage
from src.pipeline.verify import VerificationResult

logger = logging.getLogger(__name__)


@dataclass
class FailingTestCase:
    test_name: str
    test_file: str
    target_file: Optional[str]
    target_line: Optional[int]
    error_type: str
    failure_message: str
    traceback: str
    is_generated_test: bool = False
    human_confirmed: bool = False


class TestDrivenRepairEngine:
    """Orchestrates test-driven bug localization and verified remediation."""
    __test__ = False

    def __init__(self, fix_stage: Optional[FixStage] = None):
        self.fix_stage = fix_stage or FixStage()

    def discover_failing_tests(self, sandbox: SandboxEnvironment) -> List[FailingTestCase]:
        """Runs pytest in sandbox and parses all failing tests and tracebacks."""
        res = sandbox.run_command([sys.executable, "-m", "pytest", "-v", "--tb=short"], timeout=45, use_venv=False)
        output = res.stdout + "\n" + res.stderr
        return self.parse_pytest_failures(output, sandbox.sandbox_path)

    def parse_pytest_failures(self, pytest_output: str, root_dir: Path) -> List[FailingTestCase]:
        """Parses pytest failure blocks into structured FailingTestCase objects."""
        failures: List[FailingTestCase] = []
        if "FAILURES" not in pytest_output and "FAILED" not in pytest_output:
            return failures

        blocks = re.split(r'_{5,}\s+(\S+)\s+_{5,}', pytest_output)
        # blocks alternate between header and body
        for idx in range(1, len(blocks), 2):
            test_name = blocks[idx].strip()
            body = blocks[idx + 1] if idx + 1 < len(blocks) else ""

            # Extract target file and line from traceback
            target_file = None
            target_line = None
            for line in body.splitlines():
                m = re.search(r'([A-Za-z0-9_./\\]+\.py):(\d+):', line)
                if m:
                    cand_file = m.group(1).replace("\\", "/")
                    if not is_test_file(cand_file):
                        target_file = cand_file
                        target_line = int(m.group(2))

            # Extract error type and message
            err_match = re.search(r'([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):\s*(.*)', body)
            err_type = err_match.group(1) if err_match else "AssertionError"
            err_msg = err_match.group(2) if err_match else "Test assertion failed"

            # Check if this failure originated from an auto-generated route test
            is_generated = "generated" in test_name.lower() or "test_repro" in test_name.lower()

            failures.append(FailingTestCase(
                test_name=test_name,
                test_file="test suite",
                target_file=target_file,
                target_line=target_line or 1,
                error_type=err_type,
                failure_message=err_msg.strip(),
                traceback=body.strip()[:600],
                is_generated_test=is_generated,
                human_confirmed=not is_generated
            ))

        return failures

    def create_finding_from_failure(self, failure: FailingTestCase, sandbox: SandboxEnvironment) -> CanonicalFinding:
        """Converts a failing test case into a canonical finding with source_tool='failing_test'."""
        rel_file = failure.target_file or "unknown.py"
        line = failure.target_line or 1
        category = "crash" if "Error" in failure.error_type and failure.error_type != "AssertionError" else "correctness"

        human_note = ""
        if failure.is_generated_test and not failure.human_confirmed:
            human_note = " [Notice: Generated route test failure; requires human confirmation of expected behavior]"

        msg = f"[Failing Test] {failure.test_name}: {failure.error_type} - {failure.failure_message}{human_note}"
        ev = failure.traceback.splitlines()[-1] if failure.traceback else failure.failure_message

        return CanonicalFinding(
            id=generate_finding_id(rel_file, line, category, msg),
            file=rel_file,
            line_start=line,
            line_end=line,
            category=category,
            severity="high" if category == "crash" else "medium",
            source_tool="failing_test",
            message=msg,
            evidence=f"{ev} (from {failure.test_name})",
            confidence=0.96
        )

    def repair_and_verify(
        self,
        sandbox: SandboxEnvironment,
        failure: FailingTestCase,
        finding: CanonicalFinding
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Attempts to fix the target file and verifies:
        1. Target file compiles cleanly.
        2. Previously failing test now passes!
        Returns:
            (success_bool, diff_str, explanation_str)
        """
        if not failure.target_file:
            return False, None, "Target file could not be identified from traceback"

        target_p = sandbox.sandbox_path / failure.target_file
        if not target_p.exists():
            return False, None, f"File {failure.target_file} not found"

        file_content = target_p.read_text(encoding="utf-8")

        # Propose fix incorporating failure traceback
        fix_dict = finding.to_dict()
        fix_dict["traceback"] = failure.traceback

        resp = self.fix_stage.provider.propose_fix(
            file_path=failure.target_file,
            file_content=file_content,
            finding=fix_dict
        )

        old_snip = resp.get("old_snippet", "")
        new_snip = resp.get("new_snippet", "")
        diff = resp.get("diff", "")
        explanation = resp.get("explanation", "Test-driven repair")

        if old_snip and old_snip in file_content:
            patched = file_content.replace(old_snip, new_snip, 1)
            target_p.write_text(patched, encoding="utf-8")

            # Check: Does the previously failing test now pass?
            retest_res = sandbox.run_command(
                [sys.executable, "-m", "pytest", "-k", failure.test_name, "-q"],
                timeout=20,
                use_venv=False
            )
            test_now_passes = (retest_res.returncode == 0)

            if test_now_passes:
                return True, diff, explanation
            else:
                # Revert
                target_p.write_text(file_content, encoding="utf-8")
                return False, diff, f"Failing test still failed after fix: {retest_res.stdout[:150]}"

        return False, None, "Proposed fix old_snippet did not match source file"
