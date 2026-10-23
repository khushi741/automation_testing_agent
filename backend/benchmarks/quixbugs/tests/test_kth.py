import pytest
from programs.kth import kth

def test_kth():
    assert kth([4, 2, 5, 8, 1], 2) == 4
    assert kth([1, 2, 3, 4, 5], 0) == 1
