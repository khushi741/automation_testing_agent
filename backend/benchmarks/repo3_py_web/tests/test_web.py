import pytest
from app import calculate_final_invoice, get_routes


def test_standard_invoice():
    # subtotal=100, discount=10, tax=5% -> 90 + 5 = 95.0
    res = calculate_final_invoice(100.0, 10.0, 0.05)
    assert res == 95.0


def test_routes_list():
    routes = get_routes()
    assert "/" in routes
    assert "/order/checkout" in routes
