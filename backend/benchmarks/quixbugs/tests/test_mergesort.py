import pytest
from programs.mergesort import mergesort

def test_mergesort():
    assert mergesort([5, 2, 4, 1]) == [1, 2, 4, 5]
    assert mergesort([3, 1]) == [1, 3]
