"""
Sandbox Manager for HealAgent 2.0.
Provides isolated execution environments for untrusted/inspected repositories.
Sets up dedicated virtual environments, installs dependencies, and runs sandboxed commands.
Designed to be extended with Docker container isolation in future iterations.
"""
import os
import sys
import shutil
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.config import SANDBOX_ROOT, TRUSTED_REPOS, ALLOW_ALL_REPOS, WORKSPACE_DIR

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when an untrusted or prohibited repository source is requested."""
    pass


@dataclass
class SandboxEnvironment:
    """Represents an active, isolated sandbox environment for a repository."""
    sandbox_id: str
    sandbox_path: Path
    venv_path: Path
    venv_python: str
    venv_pip: str
    status: str = "initialized"  # initialized, venv_created, dependencies_installed, setup_failed
    dependency_status: str = "none"  # none, installed, failed, skipped
    setup_log: List[str] = field(default_factory=list)
    docker_mode: bool = False

    def log(self, message: str):
        logger.info(f"[Sandbox-{self.sandbox_id}] {message}")
        self.setup_log.append(message)

    def run_command(
        self,
        command: List[str],
        timeout: int = 60,
        env_vars: Optional[Dict[str, str]] = None,
        use_venv: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Executes a command safely inside the sandbox directory.
        If use_venv is True and command[0] is 'python' or 'pytest', replaces it
        with the sandbox's virtualenv interpreter.
        """
        exec_cmd = list(command)
        if use_venv and self.venv_python and os.path.exists(self.venv_python):
            if exec_cmd[0] in ("python", "python3"):
                exec_cmd[0] = self.venv_python
            elif exec_cmd[0] == "pytest":
                exec_cmd = [self.venv_python, "-m", "pytest"] + exec_cmd[1:]
            elif exec_cmd[0] == "pip":
                exec_cmd = [self.venv_python, "-m", "pip"] + exec_cmd[1:]

        run_env = os.environ.copy()
        # Prepend sandbox venv bin/Scripts to PATH
        venv_bin = str(Path(self.venv_python).parent)
        run_env["PATH"] = f"{venv_bin}{os.pathsep}{run_env.get('PATH', '')}"
        run_env["VIRTUAL_ENV"] = str(self.venv_path)
        # Sandbox isolation: disable dangerous write variables
        run_env["PYTHONDONTWRITEBYTECODE"] = "1"
        sandbox_git = self.sandbox_path / ".git"
        if sandbox_git.exists():
            run_env["GIT_DIR"] = str(sandbox_git)
            run_env["GIT_WORK_TREE"] = str(self.sandbox_path)
        if env_vars:
            run_env.update(env_vars)

        # Docker execution mode (if enabled and docker is available)
        if self.docker_mode and shutil.which("docker"):
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{self.sandbox_path.resolve().as_posix()}:/app",
                "-w", "/app",
                "python:3.11-slim"
            ] + exec_cmd
            self.log(f"Running command via Docker container: {' '.join(docker_cmd)} (timeout={timeout}s)")
            try:
                return subprocess.run(
                    docker_cmd,
                    cwd=str(self.sandbox_path),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=False
                )
            except Exception as e:
                self.log(f"Docker command failed: {e}. Falling back to local sandbox execution.")

        self.log(f"Running command: {' '.join(exec_cmd)} (timeout={timeout}s)")
        try:
            result = subprocess.run(
                exec_cmd,
                cwd=str(self.sandbox_path),
                env=run_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False
            )
            return result
        except subprocess.TimeoutExpired as e:
            self.log(f"Command timed out after {timeout} seconds: {' '.join(exec_cmd)}")
            raise e

    def cleanup(self):
        """Removes the sandbox directory and all virtualenv files."""
        if self.sandbox_path.exists():
            self.log("Cleaning up sandbox directory...")
            try:
                shutil.rmtree(self.sandbox_path, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Error during sandbox cleanup: {e}")


class SandboxManager:
    """Manages creation, trust validation, and environment setup for sandboxes."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or SANDBOX_ROOT
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def is_repo_trusted(self, repo_source: str) -> bool:
        """
        Validates if repository is in the allowlist.
        Only trusted benchmark repos or explicitly configured repos are permitted.
        """
        from src.config import is_repo_allowed
        return is_repo_allowed(repo_source)

    def create_sandbox(
        self,
        repo_source: str,
        sandbox_id: str,
        install_dependencies: bool = True
    ) -> SandboxEnvironment:
        """
        1. Validates repository trust.
        2. Copies local repo or clones git repo into sandbox directory.
        3. Creates isolated virtual environment.
        4. Installs dependencies from requirements.txt / pyproject.toml if present.
        """
        if not self.is_repo_trusted(repo_source):
            raise SecurityError(
                f"Repository '{repo_source}' is not in the trusted allowlist. "
                "In MVP mode, only benchmark and explicitly trusted repos can be analyzed."
            )

        sandbox_dir = self.root_dir / sandbox_id
        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir, ignore_errors=True)
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Creating sandbox at {sandbox_dir} for source '{repo_source}'")

        # Ingest files into sandbox
        source_path = Path(repo_source)
        if not source_path.is_absolute():
            source_path = (WORKSPACE_DIR / repo_source).resolve()

        if source_path.exists() and source_path.is_dir():
            # Copy local directory into sandbox
            for item in source_path.iterdir():
                if item.name in (".git", ".venv", "venv", "__pycache__", "node_modules"):
                    continue
                dest = sandbox_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                else:
                    shutil.copy2(item, dest)
        elif repo_source.startswith("http://") or repo_source.startswith("https://"):
            # Git clone shallow
            clone_cmd = ["git", "clone", "--depth", "1", repo_source, str(sandbox_dir)]
            res = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                raise RuntimeError(f"Git clone failed: {res.stderr.strip()}")
        else:
            raise FileNotFoundError(f"Source repository path '{repo_source}' does not exist.")

        # Determine venv location
        venv_path = sandbox_dir / ".sandbox_venv"
        if sys.platform == "win32":
            venv_python = str(venv_path / "Scripts" / "python.exe")
            venv_pip = str(venv_path / "Scripts" / "pip.exe")
        else:
            venv_python = str(venv_path / "bin" / "python")
            venv_pip = str(venv_path / "bin" / "pip")

        env = SandboxEnvironment(
            sandbox_id=sandbox_id,
            sandbox_path=sandbox_dir,
            venv_path=venv_path,
            venv_python=venv_python,
            venv_pip=venv_pip,
            status="initialized"
        )
        env.log(f"Sandbox created at {sandbox_dir}")

        # Setup virtual environment
        self._setup_virtualenv(env)

        # Install dependencies if requested
        if install_dependencies and env.status != "setup_failed":
            self._install_dependencies(env)

        return env

    def _setup_virtualenv(self, env: SandboxEnvironment):
        """Creates the isolated virtual environment using the host Python."""
        env.log("Creating isolated virtualenv (.sandbox_venv)...")
        # Use host sys.executable to build the virtual environment
        cmd = [sys.executable, "-m", "venv", str(env.venv_path)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0 and os.path.exists(env.venv_python):
                env.status = "venv_created"
                env.log("Virtualenv created successfully.")
            else:
                env.status = "setup_failed"
                env.log(f"Virtualenv creation failed: {res.stderr.strip() or res.stdout.strip()}")
        except Exception as e:
            env.status = "setup_failed"
            env.log(f"Virtualenv creation encountered error: {e}")

    def _install_dependencies(self, env: SandboxEnvironment):
        """Discovers requirements.txt / pyproject.toml and installs dependencies into the sandbox venv."""
        req_file = env.sandbox_path / "requirements.txt"
        
        # Install pytest inside the sandbox virtualenv so it can execute the repo's test suite
        try:
            env.log("Ensuring pytest is available in sandbox venv...")
            env.run_command(["pip", "install", "pytest"], timeout=60, use_venv=True)
        except Exception as e:
            env.log(f"Warning: Failed to install pytest in sandbox venv: {e}")

        if req_file.exists():
            env.log("Found requirements.txt. Installing dependencies...")
            try:
                res = env.run_command(
                    ["pip", "install", "-r", "requirements.txt"],
                    timeout=90,
                    use_venv=True
                )
                if res.returncode == 0:
                    env.dependency_status = "installed"
                    env.status = "dependencies_installed"
                    env.log("Dependencies installed successfully.")
                else:
                    env.dependency_status = "failed"
                    env.log(f"Dependency install warning: {res.stderr.strip()[:300]}")
            except subprocess.TimeoutExpired:
                env.dependency_status = "failed"
                env.log("Dependency installation timed out after 90s.")
            except Exception as e:
                env.dependency_status = "failed"
                env.log(f"Dependency install error: {e}")
        else:
            env.dependency_status = "none"
            env.log("No requirements.txt found; skipping package installation.")
