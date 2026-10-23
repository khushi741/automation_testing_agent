def gcd(a: int, b: int) -> int:
    if b == 0:
        return a
    else:
        # Bug: reversed argument order
        return gcd(a % b, b)
