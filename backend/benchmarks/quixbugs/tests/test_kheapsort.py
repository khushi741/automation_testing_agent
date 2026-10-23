import pytest
from programs.kheapsort import kheapsort

def test_kheapsort():
    assert kheapsort([3, 2, 1, 5, 4], 2) == [1, 2, 3, 4, 5]
