import time


def compute_harmonic_mean(numbers):
    """
    Computes harmonic mean: len(numbers) / sum(1/x).
    INTENTIONAL BUG (Crash): ZeroDivisionError when any number in numbers is 0,
    or when numbers is empty!
    """
    if not numbers:
        return 0.0
    reciprocal_sum = sum(1.0 / x for x in numbers)
    return len(numbers) / reciprocal_sum


def get_first_and_last(items):
    """
    Returns tuple of (first, last) element.
    INTENTIONAL BUG (Crash): IndexError when items is empty!
    """
    return items[0], items[-1]


def calculate_compound_interest(principal: float, annual_rate: float, years: int) -> float:
    """
    Calculates final amount with compound interest compounded annually: P * (1 + r)^t.
    INTENTIONAL BUG (Logic): Off-by-one in years calculation (uses years - 1 instead of years)!
    """
    if principal < 0 or annual_rate < 0 or years < 0:
        return 0.0
    # Bug: subtracted 1 from years
    return round(principal * ((1.0 + annual_rate) ** (years - 1)), 2)


def compute_fibonacci_slow(n: int) -> int:
    """
    INTENTIONAL BUG (Performance Hotspot):
    Exponential O(2^N) recursion without memoization/iteration.
    """
    if n <= 0:
        return 0
    if n == 1:
        return 1
    return compute_fibonacci_slow(n - 1) + compute_fibonacci_slow(n - 2)
