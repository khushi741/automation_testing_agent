# AUTO-GENERATED REPRODUCTION TEST SUITE - SEPARATE FROM ORIGINAL BENCHMARK TESTS
import pytest
from calculator import calculate_average, get_user_domain


def test_repro_calculate_average_empty():
    assert calculate_average([]) == 0.0


def test_repro_get_user_domain_edge_cases():
    assert get_user_domain({"name": "NoAt", "email": "abc"}) == ""
    assert get_user_domain({"name": "Empty", "email": ""}) == ""
    assert get_user_domain({"name": "NoneEmail", "email": None}) == ""
    assert get_user_domain({"name": "Valid", "email": "a@b.com"}) == "b.com"
