import pytest
from programs.rpn_eval import rpn_eval

def test_rpn_eval():
    assert rpn_eval([5, 2, "-"]) == 3
    assert rpn_eval([10, 2, "/"]) == 5
