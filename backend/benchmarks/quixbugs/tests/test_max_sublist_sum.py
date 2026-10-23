import pytest
from programs.max_sublist_sum import max_sublist_sum

def test_max_sublist_sum():
    assert max_sublist_sum([1, 2, 3]) == 6
    assert max_sublist_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
    assert max_sublist_sum([-5, -2, -9]) == -2
