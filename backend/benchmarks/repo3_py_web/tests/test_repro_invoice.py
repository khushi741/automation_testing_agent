# AUTO-GENERATED REPRODUCTION TEST SUITE - SEPARATE FROM ORIGINAL BENCHMARK TESTS
import pytest
from app import calculate_final_invoice


def test_repro_invoice_pretax_discount_exact_amounts():
    # Subtotal 50, discount 100 -> total 0.00 and $0 tax
    assert calculate_final_invoice(50.0, 100.0, 0.05) == 0.00
    # Subtotal 100, discount 20, tax 5% on 80 -> 84.00
    assert calculate_final_invoice(100.0, 20.0, 0.05) == 84.00
