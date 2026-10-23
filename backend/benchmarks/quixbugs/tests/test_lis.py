import pytest
from programs.lis import lis

def test_lis():
    assert lis([10, 22, 9, 33, 21, 50, 41, 60]) == 5
    assert lis([3, 10, 2, 1, 20]) == 3
