import pytest
from programs.flatten import flatten

def test_flatten():
    assert flatten([[1, [2]], 3]) == [1, 2, 3]
    assert flatten([1, 2, 3]) == [1, 2, 3]
