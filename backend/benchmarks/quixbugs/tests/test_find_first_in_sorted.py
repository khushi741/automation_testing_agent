import pytest
from programs.find_first_in_sorted import find_first_in_sorted

def test_find_first_in_sorted():
    assert find_first_in_sorted([1, 2, 2, 3], 2) == 1
    assert find_first_in_sorted([1, 2, 3, 4], 5) == -1
    assert find_first_in_sorted([2, 2, 2], 2) == 0
