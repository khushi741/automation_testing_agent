import pytest
from programs.sieve import sieve

def test_sieve():
    assert sieve(20) == [2, 3, 5, 7, 11, 13, 17, 19]
