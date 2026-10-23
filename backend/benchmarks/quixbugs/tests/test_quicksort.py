import pytest
from programs.quicksort import quicksort

def test_quicksort():
    assert quicksort([3, 1, 4, 1, 5, 9, 2, 6]) == [1, 1, 2, 3, 4, 5, 6, 9]
    assert quicksort([2, 2, 2]) == [2, 2, 2]
