def calculate_final_invoice(subtotal: float, discount: float, tax_rate: float = 0.05) -> float:
    """
    Calculates final invoice price.
    INTENTIONAL BUG: When discount > subtotal, total becomes negative instead of capping at 0!
    """
    tax = subtotal * tax_rate
    total = (subtotal - discount) + tax
    return round(total, 2)


def get_routes():
    return ["/", "/order/checkout", "/order/status"]
