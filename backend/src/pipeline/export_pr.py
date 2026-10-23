"""
Export & GitHub PR Creator for HealAgent 2.0.
Responsible for:
1. Creating dedicated branch `healagent-fixes-{run_id}`.
2. Committing each verified fix individually (commit-per-fix).
3. Redacting any sensitive tokens, secrets, or keys.
4. Optional token-gated GitHub Pull Request creation via GitHub REST API.
"""
import os
import re
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

SECRET_PATTERNS = [
    r'AIza[0-9A-Za-z-_]{35}',
    r'ghp_[0-9A-Za-z]{36}',
    r'sk-[0-9A-Za-z]{32,}',
    r'bearer\s+[0-9A-Za-z-_.]+',
    r'(?:password|secret|token)\s*=\s*["\'][^"\']+["\']'
]


def redact_secrets(text: str) -> str:
    """Sanitizes text by replacing any API tokens, keys, or passwords with redacted placeholders."""
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED_SECRET]", sanitized, flags=re.IGNORECASE)
    return sanitized


class GitBranchExporter:
    """Manages creation of commit-per-fix git branches and PRs."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir

    def create_commit_per_fix_branch(
        self,
        run_id: str,
        verified_patches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Creates a branch `healagent-fixes-{run_id}`, applies verified patches one by one,
        and creates a separate git commit for each patch.
        """
        branch_name = f"healagent-fixes-{run_id[:8]}"
        commits_created: List[Dict[str, str]] = []

        try:
            # 1. Checkout new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                check=True
            )

            # 2. Apply and commit each verified fix
            for patch in verified_patches:
                file_rel = patch.get("file", "")
                finding_msg = patch.get("message", "Issue resolved")
                category = patch.get("category", "fix")
                model_name = patch.get("model_name", "gemini")

                file_path = self.repo_dir / file_rel
                new_content = patch.get("new_content")
                if new_content and file_path.exists():
                    file_path.write_text(new_content, encoding="utf-8")

                # Stage file
                subprocess.run(["git", "add", file_rel], cwd=str(self.repo_dir), check=True)

                # Commit
                commit_title = f"fix({category}): {finding_msg[:60]}"
                commit_body = (
                    f"Automated fix verified by HealAgent 2.0\n\n"
                    f"- File: {file_rel}\n"
                    f"- Model: {model_name}\n"
                    f"- Checks Passed: Syntax/Linter, Existing Tests, Dynamic Trigger\n"
                )
                safe_msg = redact_secrets(f"{commit_title}\n\n{commit_body}")

                proc = subprocess.run(
                    ["git", "commit", "-m", safe_msg],
                    cwd=str(self.repo_dir),
                    capture_output=True,
                    text=True
                )
                commit_hash = "local"
                rev = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=str(self.repo_dir),
                    capture_output=True,
                    text=True
                )
                if rev.returncode == 0:
                    commit_hash = rev.stdout.strip()

                commits_created.append({
                    "file": file_rel,
                    "commit_hash": commit_hash,
                    "message": commit_title
                })

            return {
                "success": True,
                "branch_name": branch_name,
                "commits_count": len(commits_created),
                "commits": commits_created
            }

        except Exception as e:
            logger.error(f"Failed to create fix branch: {e}")
            return {
                "success": False,
                "error": str(e),
                "branch_name": branch_name,
                "commits": []
            }

    def create_github_pr(
        self,
        repo_owner_name: str,
        branch_name: str,
        base_branch: str = "main",
        github_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a Pull Request on GitHub using the provided GITHUB_TOKEN."""
        token = github_token or os.environ.get("GITHUB_TOKEN")
        if not token:
            return {
                "success": False,
                "error": "GITHUB_TOKEN not provided; PR creation skipped (branch created locally)."
            }

        import urllib.request
        import json

        url = f"https://api.github.com/repos/{repo_owner_name}/pulls"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        payload = {
            "title": f"[HealAgent 2.0] Automated Verified Fixes from branch {branch_name}",
            "head": branch_name,
            "base": base_branch,
            "body": redact_secrets(
                "## HealAgent 2.0 Autonomous Fixes\n\n"
                "This PR was generated automatically by HealAgent 2.0.\n"
                "All included patches passed the 3-check verification:\n"
                "1. Clean syntax & strict linter pass\n"
                "2. All pre-existing test suites passed without regression\n"
                "3. Dynamic crash/logic trigger confirmed resolved\n\n"
                "> Note: Passing tests does not guarantee unchanged business behavior. Please review assumptions."
            )
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "pr_url": data.get("html_url"),
                    "pr_number": data.get("number")
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create GitHub PR: {e}"
            }
