import pytest
from programs.levenshtein import levenshtein

def test_levenshtein():
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("rosettacode", "raisethysword") == 8
