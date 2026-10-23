def sqrt(x: float, epsilon: float) -> float:
    approx = 0.5 * x
    while abs(x - approx * approx) > epsilon:
        # Bug: approx = 2 * approx instead of Newton-Raphson step
        approx = 2.0 * approx
    return approx
