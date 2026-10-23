"""
Unit tests for TestDrivenRepairEngine.
"""
from pathlib import Path
import pytest

from src.pipeline.test_driven_repair import TestDrivenRepairEngine, FailingTestCase


def test_parse_pytest_failures():
    sample_output = """
=================================== FAILURES ===================================
__________________________ test_repro_coupon_active ___________________________

    def test_repro_coupon_active():
>       assert is_coupon_valid(1000, 500) is True
E       AssertionError: assert False is True

api_service.py:32: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_api_service.py::test_repro_coupon_active - AssertionError: assert False is True
============================== 1 failed in 0.05s ===============================
"""
    engine = TestDrivenRepairEngine()
    failures = engine.parse_pytest_failures(sample_output, Path("."))
    assert len(failures) == 1
    f = failures[0]
    assert f.test_name == "test_repro_coupon_active"
    assert f.target_file == "api_service.py"
    assert f.target_line == 32
    assert "AssertionError" in f.error_type
    assert f.is_generated_test is True  # test_repro prefix flags as generated/repro


def test_create_finding_from_failing_test():
    engine = TestDrivenRepairEngine()
    failure = FailingTestCase(
        test_name="test_generated_route_checkout",
        test_file="test_routes.py",
        target_file="app.py",
        target_line=45,
        error_type="ZeroDivisionError",
        failure_message="division by zero",
        traceback="app.py:45: ZeroDivisionError: division by zero",
        is_generated_test=True,
        human_confirmed=False
    )
    finding = engine.create_finding_from_failure(failure, None)
    assert finding.source_tool == "failing_test"
    assert finding.category == "crash"
    assert "human confirmation" in finding.message.lower()
