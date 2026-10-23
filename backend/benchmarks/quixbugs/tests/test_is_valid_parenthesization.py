import pytest
from programs.is_valid_parenthesization import is_valid_parenthesization

def test_parens():
    assert is_valid_parenthesization("()") is True
    assert is_valid_parenthesization("(()())") is True
    assert is_valid_parenthesization(")(") is False
    assert is_valid_parenthesization("(((") is False
