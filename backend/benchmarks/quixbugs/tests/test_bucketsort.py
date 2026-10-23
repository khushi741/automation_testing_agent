import pytest
from programs.bucketsort import bucketsort

def test_bucketsort():
    assert bucketsort([3, 1, 1, 2], 4) == [1, 1, 2, 3]
    assert bucketsort([0, 2, 1], 3) == [0, 1, 2]
