"""
Stage 3: Fix — Context-slice extraction, minimal snippet replacement,
SIMPLIFY pass, unified diff generation in code, and database persistence.
"""
import os
import ast
import uuid
import difflib
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

from database import SessionLocal
from models import Patch, Finding
from src.pipeline.detect import CanonicalFinding
from src.pipeline.sandbox import SandboxEnvironment
from src.llm.provider import BaseLLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


@dataclass
class ProposedPatch:
    """Represents a proposed fix patch generated for a finding."""
    patch_id: str
    finding_id: str
    file: str
    old_snippet: str
    new_snippet: str
    diff_content: str
    explanation: str
    lines_added: int
    lines_removed: int
    attempts: int
    status: str = "proposed"
    provider_used: str = ""
    model_name: str = "gemini-3.5-flash-lite"
    thinking_level: str = "standard"
    assumption: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_context_slice(file_content: str, line_start: int, line_end: int, window: int = 15) -> Tuple[str, int, int]:
    """
    Extracts a focused slice of lines around the finding (window lines before/after),
    rather than sending the entire file to the LLM.
    Returns: (slice_text, slice_start_line, slice_end_line)
    """
    lines = file_content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return "", 1, 1

    start_idx = max(0, line_start - 1 - window)
    end_idx = min(total_lines, line_end + window)

    slice_lines = lines[start_idx:end_idx]
    slice_text = "\n".join(slice_lines)
    return slice_text, start_idx + 1, end_idx


class FixStage:
    """Stage 3 Fix Orchestrator."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None, max_retries: int = 3):
        self.provider = provider or get_llm_provider()
        self.max_retries = max_retries
        self.provider_name = self.provider.__class__.__name__

    def run(
        self,
        sandbox: SandboxEnvironment,
        findings: List[CanonicalFinding],
        run_id: str
    ) -> List[ProposedPatch]:
        """
        Processes each finding, requests minimal JSON fix from provider,
        performs validation and SIMPLIFY pass, builds unified diff in code,
        and saves proposed patches to database.
        """
        logger.info(f"Starting FixStage for run {run_id} using {self.provider_name} ({len(findings)} findings)")
        proposed_patches: List[ProposedPatch] = []

        for finding in findings:
            target_path = sandbox.sandbox_path / finding.file
            if not target_path.exists():
                logger.warning(f"File {finding.file} does not exist in sandbox; skipping.")
                continue

            try:
                file_content = target_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.warning(f"Could not read {finding.file}: {e}")
                continue

            # Step 1: Extract focused context slice (about 20-30 lines)
            context_slice, slice_start, slice_end = extract_context_slice(
                file_content, finding.line_start, finding.line_end, window=12
            )

            # Step 2: Request JSON fix with retry loop (max 3)
            fix_result, attempts = self._generate_validated_fix(
                finding=finding,
                file_content=file_content,
                context_slice=context_slice
            )

            if not fix_result or not fix_result.get("old_snippet"):
                logger.info(f"Finding {finding.id} has no safe automated fix. Marking as needs_review.")
                patch_id = f"patch_{uuid.uuid4().hex[:12]}"
                needs_review_patch = ProposedPatch(
                    patch_id=patch_id,
                    finding_id=finding.id,
                    file=finding.file,
                    old_snippet="",
                    new_snippet="",
                    diff_content="",
                    explanation="No safe behavior-preserving automated fix found; requires human review.",
                    lines_added=0,
                    lines_removed=0,
                    attempts=attempts,
                    status="needs_review",
                    provider_used=self.provider_name
                )
                self._save_patch_to_db(needs_review_patch, run_id, failure_reason="No safe automated fix available")
                proposed_patches.append(needs_review_patch)
                continue

            old_snippet = fix_result["old_snippet"]
            new_snippet = fix_result["new_snippet"]
            explanation = fix_result.get("explanation", "Fix proposed")

            # Step 3: Run SIMPLIFY pass
            simplified = self._run_simplify_pass(
                old_snippet=old_snippet,
                new_snippet=new_snippet,
                context_slice=context_slice,
                file_content=file_content
            )
            old_snippet = simplified["old_snippet"]
            new_snippet = simplified["new_snippet"]
            if simplified.get("explanation"):
                explanation = f"{explanation} | {simplified['explanation']}"

            # Step 4: Build unified diff in code
            diff_content = self._build_unified_diff(
                file_path=finding.file,
                file_content=file_content,
                old_snippet=old_snippet,
                new_snippet=new_snippet
            )

            lines_added = len(new_snippet.splitlines())
            lines_removed = len(old_snippet.splitlines())
            patch_id = f"patch_{uuid.uuid4().hex[:12]}"

            # Detect assumptions for human confirmation
            assumption = None
            if any(k in explanation.lower() for k in ["assumption", "clamping", "discount", "dataset has no mean", "capped at", "clamped"]):
                assumption = explanation

            model_used = fix_result.get("model_name") or getattr(self.provider, "model", "gemini-3.5-flash-lite")
            thinking_used = fix_result.get("thinking_level") or getattr(self.provider, "thinking_level", "standard")

            proposed_patch = ProposedPatch(
                patch_id=patch_id,
                finding_id=finding.id,
                file=finding.file,
                old_snippet=old_snippet,
                new_snippet=new_snippet,
                diff_content=diff_content,
                explanation=explanation,
                lines_added=lines_added,
                lines_removed=lines_removed,
                attempts=attempts,
                status="proposed",
                provider_used=self.provider_name,
                model_name=model_used,
                thinking_level=thinking_used,
                assumption=assumption
            )

            proposed_patches.append(proposed_patch)

        # Step 5: Multi-patch conflict detection per file
        final_patches = self._resolve_file_conflicts(proposed_patches, run_id)

        # Save valid patches to DB
        for p in final_patches:
            if p.status == "proposed":
                self._save_patch_to_db(p, run_id)

        logger.info(f"FixStage complete: {len(final_patches)} patches processed.")
        return final_patches

    def _resolve_file_conflicts(self, patches: List[ProposedPatch], run_id: str) -> List[ProposedPatch]:
        """
        Detects conflicts between multiple patches touching the same file.
        E.g., if Patch A removes 'import os' as unused, but Patch B adds 'os.getenv',
        Patch A is marked 'needs_review' due to conflict with Patch B.
        """
        resolved: List[ProposedPatch] = []
        # Group by file
        by_file: Dict[str, List[ProposedPatch]] = {}
        for p in patches:
            by_file.setdefault(p.file, []).append(p)

        for file_name, file_patches in by_file.items():
            # Check what modules/symbols are introduced across all proposed patches
            introduced_symbols = set()
            for p in file_patches:
                if p.status == "proposed":
                    for sym in ["os.", "sys.", "re.", "json.", "math.", "sqlite3."]:
                        if sym in p.new_snippet:
                            introduced_symbols.add(sym.rstrip("."))

            for p in file_patches:
                # If this patch deletes an import that is introduced by another patch
                if p.status == "proposed" and p.old_snippet.strip().startswith(("import ", "from ")):
                    mod_deleted = p.old_snippet.strip().split()[1]
                    if mod_deleted in introduced_symbols:
                        p.status = "needs_review"
                        p.explanation = f"Conflict: '{mod_deleted}' is required by another companion patch in {file_name}."
                        self._save_patch_to_db(p, run_id, failure_reason=p.explanation)
                        logger.info(f"Resolved conflict: Dropped import deletion of '{mod_deleted}' required by companion patch.")
                resolved.append(p)

        return resolved

    def _generate_validated_fix(
        self,
        finding: CanonicalFinding,
        file_content: str,
        context_slice: str
    ) -> Tuple[Optional[Dict[str, str]], int]:
        """
        Prompts the provider for a fix, validating:
        1. Exact single occurrence of old_snippet in file_content.
        2. Non-empty replacement.
        3. Line growth constraints (lines_added <= 2 * lines_removed + 5 unless security).
        4. Valid Python syntax after in-memory substitution.
        Retries up to max_retries.
        """
        finding_dict = finding.to_dict()
        last_error = ""

        for attempt in range(1, self.max_retries + 1):
            try:
                # Add failure feedback to finding dictionary if retrying
                if last_error:
                    finding_dict["previous_attempt_error"] = last_error

                resp = self.provider.propose_fix(
                    file_path=finding.file,
                    context_slice=context_slice,
                    finding=finding_dict
                )

                old_snip = resp.get("old_snippet", "")
                new_snip = resp.get("new_snippet", "")

                if not old_snip:
                    last_error = "old_snippet was empty"
                    continue

                # Normalize newlines for robust cross-platform matching
                file_norm = file_content.replace("\r\n", "\n")
                old_snip = old_snip.replace("\r\n", "\n")
                new_snip = new_snip.replace("\r\n", "\n")

                # Validation 1: Must appear in file
                match_count = file_norm.count(old_snip)
                if match_count == 0:
                    last_error = f"old_snippet does not match verbatim text in {finding.file}"
                    continue

                # Validation 2: Must appear exactly once to prevent ambiguous replacement
                if match_count > 1:
                    last_error = f"old_snippet appeared {match_count} times; must include surrounding lines to be unique"
                    continue

                # Validation 3: Line growth gate (reject bloat)
                added = len(new_snip.splitlines())
                removed = len(old_snip.splitlines())
                if finding.category != "security" and added > (2 * removed + 5):
                    last_error = f"Fix added {added} lines compared to {removed} removed; excessive line growth rejected"
                    continue

                # Validation 4: Syntax check after in-memory application
                patched_content = file_norm.replace(old_snip, new_snip, 1)
                try:
                    ast.parse(patched_content)
                except SyntaxError as syn_err:
                    last_error = f"Applied fix introduced Python SyntaxError: {syn_err}"
                    continue

                # Passed all validations!
                return resp, attempt

            except Exception as e:
                last_error = f"Provider error: {e}"

        logger.warning(f"Fix generation exhausted all {self.max_retries} attempts: {last_error}")
        return None, self.max_retries

    def _run_simplify_pass(
        self,
        old_snippet: str,
        new_snippet: str,
        context_slice: str,
        file_content: str
    ) -> Dict[str, str]:
        """Runs the secondary SIMPLIFY pass to minimize lines and complexity."""
        try:
            simplified = self.provider.simplify_fix(
                old_snippet=old_snippet,
                new_snippet=new_snippet,
                context_slice=context_slice
            )
            sim_old = simplified.get("old_snippet", "")
            sim_new = simplified.get("new_snippet", "")

            # Verify simplified version still matches uniquely and has fewer or equal lines
            if (
                sim_old == old_snippet
                and file_content.count(sim_old) == 1
                and len(sim_new.splitlines()) <= len(new_snippet.splitlines())
            ):
                # Guard against line-length regressions (>88 chars)
                sim_max = max((len(l) for l in sim_new.splitlines()), default=0)
                orig_max = max((len(l) for l in new_snippet.splitlines()), default=0)
                if sim_max > 88 and orig_max <= 88:
                    return {"old_snippet": old_snippet, "new_snippet": new_snippet, "explanation": "Retained multi-line fix to prevent line length exceeding 88 characters"}

                # Verify syntax
                patched = file_content.replace(sim_old, sim_new, 1)
                ast.parse(patched)
                return simplified
        except Exception as e:
            logger.debug(f"Simplify pass rejected or errored: {e}")

        return {"old_snippet": old_snippet, "new_snippet": new_snippet, "explanation": "Kept original fix"}

    def _build_unified_diff(
        self,
        file_path: str,
        file_content: str,
        old_snippet: str,
        new_snippet: str
    ) -> str:
        """Constructs a standard unified diff in code using Python's difflib."""
        old_lines = file_content.splitlines(keepends=True)
        patched_content = file_content.replace(old_snippet, new_snippet, 1)
        new_lines = patched_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=3
        )
        return "".join(diff)

    def _save_patch_to_db(self, patch: ProposedPatch, run_id: str, failure_reason: Optional[str] = None):
        """Persists patch record in database with its status."""
        db = SessionLocal()
        try:
            db_patch = db.query(Patch).filter(Patch.id == patch.patch_id).first()
            if not db_patch:
                db_patch = Patch(
                    id=patch.patch_id,
                    finding_id=patch.finding_id,
                    run_id=run_id,
                    diff_content=patch.diff_content,
                    old_snippet=patch.old_snippet,
                    new_snippet=patch.new_snippet,
                    status=patch.status,
                    failure_reason=failure_reason,
                    attempts=patch.attempts,
                    lines_added=patch.lines_added,
                    lines_removed=patch.lines_removed,
                    explanation=patch.explanation,
                    model_name=getattr(patch, "model_name", "gemini-3.5-flash-lite"),
                    thinking_level=getattr(patch, "thinking_level", "standard"),
                    assumption=getattr(patch, "assumption", None)
                )
                db.add(db_patch)
            else:
                db_patch.status = patch.status
                db_patch.failure_reason = failure_reason
                db_patch.explanation = patch.explanation
                db_patch.model_name = getattr(patch, "model_name", "gemini-3.5-flash-lite")
                db_patch.thinking_level = getattr(patch, "thinking_level", "standard")
                db_patch.assumption = getattr(patch, "assumption", None)

            db.commit()
            logger.info(f"Saved patch {patch.patch_id} (status: {patch.status}) to database.")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save patch to database: {e}")
        finally:
            db.close()
