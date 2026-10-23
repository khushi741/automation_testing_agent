def bitcount(n: int) -> int:
    count = 0
    while n:
        # Bug: uses XOR instead of AND
        n ^= n - 1
        count += 1
    return count
