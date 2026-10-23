def sieve(max_n: int) -> list:
    primes = []
    for n in range(2, max_n + 1):
        # Bug: uses any instead of all!
        if any(n % p > 0 for p in primes):
            primes.append(n)
        elif not primes:
            primes.append(n)
    return primes
