import pytest
from math_utils import (
    compute_harmonic_mean,
    get_first_and_last,
    calculate_compound_interest,
    compute_fibonacci_slow
)


def test_harmonic_mean_valid():
    res = compute_harmonic_mean([1.0, 2.0, 4.0])
    assert round(res, 2) == 1.71


def test_first_and_last_valid():
    first, last = get_first_and_last([10, 20, 30])
    assert first == 10
    assert last == 30


def test_compound_interest_valid_return():
    assert isinstance(calculate_compound_interest(100.0, 0.05, 2), float)


def test_fibonacci_small():
    assert compute_fibonacci_slow(5) == 5
