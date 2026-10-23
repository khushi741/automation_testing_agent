def get_factors(n: int) -> list:
    if n == 1:
        return []
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            # Bug: recurses on n instead of n // i
            return [i] + get_factors(n)
    return [n]
