import pytest
from programs.knapsack import knapsack

def test_knapsack():
    assert knapsack(10, [(3, 2), (4, 3), (5, 4)]) == 7
