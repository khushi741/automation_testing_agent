import pytest
from programs.get_factors import get_factors

def test_get_factors():
    assert get_factors(12) == [2, 2, 3]
    assert get_factors(7) == [7]
