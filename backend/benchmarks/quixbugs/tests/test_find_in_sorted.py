import pytest
from programs.find_in_sorted import find_in_sorted

def test_find_in_sorted():
    assert find_in_sorted([1, 3, 5, 7], 5) == 2
    assert find_in_sorted([1, 3, 5, 7], 2) == -1
