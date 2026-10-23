import pytest
from programs.sqrt import sqrt

def test_sqrt():
    assert abs(sqrt(4.0, 0.01) - 2.0) < 0.05
    assert abs(sqrt(9.0, 0.01) - 3.0) < 0.05
