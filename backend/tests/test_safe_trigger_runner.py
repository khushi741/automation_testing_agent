"""
Unit tests for SafeTriggerRunner.
Verifies:
1. Trigger attempting to read .env or sensitive files is blocked.
2. Trigger attempting to open network sockets is blocked.
3. Trigger attempting to write outside temporary directory is blocked.
4. Legitimate trigger (e.g. ZeroDivisionError or IndexError) executes and confirms crash.
"""
import sys
from pathlib import Path
import pytest

from src.pipeline.safe_trigger_runner import SafeTriggerRunner


@pytest.fixture
def runner():
    return SafeTriggerRunner(timeout_seconds=5)


@pytest.fixture
def dummy_module(tmp_path):
    target = tmp_path / "dummy_calc.py"
    target.write_text("""
def divide(a, b):
    return a / b

def get_item(lst, idx):
    return lst[idx]
""", encoding="utf-8")
    return target


def test_trigger_blocked_reading_env(runner, dummy_module):
    """Proves that a trigger attempting to read a .env file is blocked by security guard."""
    malicious_trigger = 'with open(".env", "r") as f: data = f.read()'
    confirmed, details = runner.run_trigger(
        target_file=dummy_module,
        trigger_code=malicious_trigger
    )
    assert not confirmed
    assert "Access to sensitive file" in details or "SECURITY_BLOCKED" in details or "blocked" in details.lower()


def test_trigger_blocked_opening_socket(runner, dummy_module):
    """Proves that a trigger attempting to open a network socket is blocked by security guard."""
    malicious_trigger = """
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("1.1.1.1", 80))
"""
    confirmed, details = runner.run_trigger(
        target_file=dummy_module,
        trigger_code=malicious_trigger
    )
    assert not confirmed
    assert "Network access is strictly forbidden" in details or "forbidden" in details.lower()


def test_trigger_blocked_writing_outside_temp_dir(runner, dummy_module, tmp_path):
    """Proves that a trigger attempting to write outside temporary directory is blocked."""
    outside_file = tmp_path / "hacked.txt"
    malicious_trigger = f'with open(r"{outside_file}", "w") as f: f.write("exploit")'
    confirmed, details = runner.run_trigger(
        target_file=dummy_module,
        trigger_code=malicious_trigger
    )
    assert not confirmed
    assert "Writing outside temporary sandbox is blocked" in details or "blocked" in details.lower()
    assert not outside_file.exists()


def test_legitimate_trigger_confirms_crash(runner, dummy_module):
    """Proves that a legitimate trigger confirms ZeroDivisionError cleanly."""
    valid_trigger = "divide(10, 0)"
    confirmed, details = runner.run_trigger(
        target_file=dummy_module,
        trigger_code=valid_trigger
    )
    assert confirmed is True
    assert "ZeroDivisionError" in details
