import pytest
from programs.bitcount import bitcount

def test_bitcount():
    assert bitcount(0) == 0
    assert bitcount(127) == 7
    assert bitcount(128) == 1
