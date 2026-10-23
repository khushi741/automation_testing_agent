import pytest
from programs.gcd import gcd

def test_gcd():
    assert gcd(35, 10) == 5
    assert gcd(13, 27) == 1
    assert gcd(48, 18) == 6
