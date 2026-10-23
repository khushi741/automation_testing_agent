"""
Safe Restricted Subprocess Trigger Runner for HealAgent 2.0.

Executes LLM-generated bug triggers inside a strictly sandboxed, restricted subprocess:
1. Isolated temporary working directory per run.
2. Minimal environment: strips all API keys, tokens, and secrets.
3. Network disabled: socket creation is blocked with PermissionError.
4. Restricted filesystem: blocks access to .env and writes outside the temporary directory.
5. Strict execution timeout (5 seconds).
"""
import os
import sys
import json
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

SAFE_ENV_ALLOWLIST = {
    "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP",
    "PYTHONPATH", "PYTHONHOME", "COMSPEC", "LANG", "LC_ALL",
    "HOMEDRIVE", "HOMEPATH", "USERPROFILE"
}


class SafeTriggerRunner:
    """Executes code triggers in an isolated, network-disabled, filesystem-restricted subprocess."""

    def __init__(self, timeout_seconds: int = 5):
        self.timeout = timeout_seconds

    def run_trigger(
        self,
        target_file: Path,
        trigger_code: str,
        evidence: str = "",
        assertion: str = "",
        message: str = ""
    ) -> Tuple[bool, str]:
        """
        Executes target file and trigger code inside a secure temporary environment.
        Returns:
            (confirmed_bool, details_str)
        """
        target_resolved = target_file.resolve()
        target_dir = target_resolved.parent

        with tempfile.TemporaryDirectory(prefix="healagent_safe_trigger_") as temp_dir:
            temp_path = Path(temp_dir).resolve()

            # Construct sterile environment without API keys
            sterile_env: Dict[str, str] = {}
            for k, v in os.environ.items():
                if k.upper() in SAFE_ENV_ALLOWLIST:
                    sterile_env[k] = v

            # Prepend target directory to PYTHONPATH so it can import target module
            current_py_path = sterile_env.get("PYTHONPATH", "")
            sterile_env["PYTHONPATH"] = f"{target_dir}{os.pathsep}{current_py_path}"
            sterile_env["PYTHONDONTWRITEBYTECODE"] = "1"

            # Write trigger payload to json to avoid any quote/backslash escaping issues
            payload_path = temp_path / "trigger_payload.json"
            payload_data = {
                "target_file": str(target_resolved),
                "target_dir": str(target_dir),
                "temp_dir": str(temp_path),
                "trigger_code": trigger_code,
                "evidence": evidence,
                "assertion": assertion,
                "message": message
            }
            payload_path.write_text(json.dumps(payload_data), encoding="utf-8")

            runner_file = temp_path / "run_safe_sandbox.py"
            runner_file.write_text('''
import sys
import os
import json
import socket
from pathlib import Path
import importlib.util

# Read payload
payload_p = Path(__file__).parent / "trigger_payload.json"
with open(payload_p, "r", encoding="utf-8") as f:
    payload = json.load(f)

ALLOWED_TEMP_DIR = Path(payload["temp_dir"]).resolve()
ALLOWED_TARGET_FILE = Path(payload["target_file"]).resolve()
ALLOWED_TARGET_DIR = Path(payload["target_dir"]).resolve()

# ─── SECURITY GUARD 1: DISABLE NETWORK ACCESS ───
def _blocked_socket(*args, **kwargs):
    raise PermissionError("Network access is strictly forbidden in safe trigger runner")

socket.socket = _blocked_socket
socket.create_connection = _blocked_socket
if hasattr(socket, "getaddrinfo"):
    socket.getaddrinfo = _blocked_socket

# ─── SECURITY GUARD 2: RESTRICTED FILESYSTEM ACCESS ───
_orig_open = open

def _safe_open(file, mode="r", *args, **kwargs):
    file_p = Path(file).resolve()
    # Check for forbidden sensitive files like .env or secrets
    if ".env" in file_p.name.lower() or "secret" in file_p.name.lower():
        raise PermissionError(f"Access to sensitive file {file_p.name} is blocked")
    
    # If writing, ensure it is STRICTLY within ALLOWED_TEMP_DIR
    if any(m in mode for m in ("w", "a", "x", "+")):
        try:
            file_p.relative_to(ALLOWED_TEMP_DIR)
        except ValueError:
            raise PermissionError(f"Writing outside temporary sandbox is blocked: {file_p}")

    return _orig_open(file, mode, *args, **kwargs)

import builtins
builtins.open = _safe_open

# ─── EXECUTE TRIGGER TARGET MODULE ───
target_p = ALLOWED_TARGET_FILE
globs = {}
try:
    spec = importlib.util.spec_from_file_location("safe_target_mod", str(target_p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    globs = {k: getattr(mod, k) for k in dir(mod)}
except Exception as e:
    pass

trigger = payload["trigger_code"]
ev = payload["evidence"]
assertion = payload["assertion"]
msg = payload["message"]

try:
    exec(trigger, globs)
    if assertion:
        try:
            exec(assertion, globs)
            print("LOGIC_SAFE_NO_BUG")
            sys.exit(0)
        except AssertionError as ae:
            print(f"CRASH_CONFIRMED:AssertionError:{ae or 'Assertion failed: ' + assertion}")
            sys.exit(0)

    if ev and ev not in trigger:
        try:
            val = eval(ev, globs)
            if "negative" in msg.lower() and isinstance(val, (int, float)) and val < 0:
                print(f"CRASH_CONFIRMED:LogicError:Negative value returned {val}")
                sys.exit(0)
        except SyntaxError:
            exec(ev, globs)
    print("NO_CRASH")
except (ZeroDivisionError, AttributeError, TypeError, IndexError, KeyError, ValueError) as crash:
    print(f"CRASH_CONFIRMED:{type(crash).__name__}:{crash}")
except AssertionError as ae:
    print(f"CRASH_CONFIRMED:AssertionError:{ae}")
except PermissionError as pe:
    print(f"SECURITY_BLOCKED:{pe}")
except Exception as other:
    print(f"OTHER_EXCEPTION:{type(other).__name__}:{other}")
''', encoding="utf-8")

            try:
                proc = subprocess.run(
                    [sys.executable, str(runner_file)],
                    cwd=str(temp_path),
                    env=sterile_env,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                out = proc.stdout.strip()
                err = proc.stderr.strip()

                if "SECURITY_BLOCKED:" in out:
                    return False, out.split("SECURITY_BLOCKED:")[1].strip()
                if "CRASH_CONFIRMED:" in out:
                    crash_info = out.split("CRASH_CONFIRMED:")[1].strip()
                    return True, crash_info
                if "LOGIC_SAFE_NO_BUG" in out or "NO_CRASH" in out:
                    return False, "Handled safely without error"

                return False, f"Trigger completed without confirming crash: {out[:120]}"

            except subprocess.TimeoutExpired:
                return True, f"Execution timed out ({self.timeout}s limit reached)"
            except Exception as e:
                return False, f"Subprocess runner failed: {e}"
