import pytest
from calculator import calculate_average, get_user_domain, sum_positive_numbers


def test_calculate_average_populated():
    res = calculate_average([10, 20, 30])
    assert res == 20.0


def test_get_user_domain_valid():
    record = {"name": "Bob", "email": "bob@domain.org"}
    domain = get_user_domain(record)
    assert domain == "domain.org"


def test_sum_positive_numbers():
    assert sum_positive_numbers([-5, 10, -2, 20]) == 30

