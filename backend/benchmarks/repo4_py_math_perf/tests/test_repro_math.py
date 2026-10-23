import pytest
from math_utils import (
    compute_harmonic_mean,
    get_first_and_last,
    calculate_compound_interest
)


def test_repro_zerodiv_harmonic_mean():
    """Reproduces ZeroDivisionError when 0 is in the input array."""
    with pytest.raises(ZeroDivisionError):
        compute_harmonic_mean([2.0, 0.0, 4.0])


def test_repro_indexerr_empty_list():
    """Reproduces IndexError when items list is empty."""
    with pytest.raises(IndexError):
        get_first_and_last([])


def test_repro_offbyone_compound_interest():
    """Reproduces off-by-one bug: 1 year interest should compound for 1 year, not 0."""
    # Under current bug (range(1, 1)): loop does not execute, returns principal without interest!
    res = calculate_compound_interest(1000.0, 0.10, 1)
    assert res == 1000.0  # Demonstrates bug: expected 1100.0
