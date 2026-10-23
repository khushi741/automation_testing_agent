import pytest
from programs.pascal import pascal

def test_pascal():
    assert pascal(4) == [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1]]
