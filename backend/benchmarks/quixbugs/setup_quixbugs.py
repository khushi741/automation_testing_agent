"""
Setup script for QuixBugs Python Benchmark (20 programs: 5 Train, 15 Holdout).
Generates the programs with their canonical seeded bugs, creates test suites,
and generates the tamper-evident hash manifest for train and holdout splits BEFORE evaluation.
"""
import hashlib
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROGRAMS_DIR = BASE_DIR / "programs"
TESTS_DIR = BASE_DIR / "tests"

PROGRAMS_DIR.mkdir(parents=True, exist_ok=True)
TESTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── 5 TRAIN PROGRAMS ────────────────────────────────────────────────────────

TRAIN_DATA = {
    "bitcount": (
'''def bitcount(n: int) -> int:
    count = 0
    while n:
        # Bug: uses XOR instead of AND
        n ^= n - 1
        count += 1
    return count
''',
'''import pytest
from programs.bitcount import bitcount

def test_bitcount():
    assert bitcount(0) == 0
    assert bitcount(127) == 7
    assert bitcount(128) == 1
'''
    ),
    "gcd": (
'''def gcd(a: int, b: int) -> int:
    if b == 0:
        return a
    else:
        # Bug: reversed argument order
        return gcd(a % b, b)
''',
'''import pytest
from programs.gcd import gcd

def test_gcd():
    assert gcd(35, 10) == 5
    assert gcd(13, 27) == 1
    assert gcd(48, 18) == 6
'''
    ),
    "is_valid_parenthesization": (
'''def is_valid_parenthesization(parens: str) -> bool:
    depth = 0
    for paren in parens:
        if paren == "(":
            depth += 1
        else:
            depth -= 1
            if depth < 0:
                # Bug: returns True when depth goes negative
                return True
    return depth == 0
''',
'''import pytest
from programs.is_valid_parenthesization import is_valid_parenthesization

def test_parens():
    assert is_valid_parenthesization("()") is True
    assert is_valid_parenthesization("(()())") is True
    assert is_valid_parenthesization(")(") is False
    assert is_valid_parenthesization("(((") is False
'''
    ),
    "max_sublist_sum": (
'''def max_sublist_sum(arr: list) -> int:
    # Bug: initialized to 0, fails on all-negative list
    max_ending_here = 0
    max_so_far = 0
    for x in arr:
        max_ending_here = max(x, max_ending_here + x)
        max_so_far = max(max_so_far, max_ending_here)
    return max_so_far
''',
'''import pytest
from programs.max_sublist_sum import max_sublist_sum

def test_max_sublist_sum():
    assert max_sublist_sum([1, 2, 3]) == 6
    assert max_sublist_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
    assert max_sublist_sum([-5, -2, -9]) == -2
'''
    ),
    "sqrt": (
'''def sqrt(x: float, epsilon: float) -> float:
    approx = 0.5 * x
    while abs(x - approx * approx) > epsilon:
        # Bug: approx = 2 * approx instead of Newton-Raphson step
        approx = 2.0 * approx
    return approx
''',
'''import pytest
from programs.sqrt import sqrt

def test_sqrt():
    assert abs(sqrt(4.0, 0.01) - 2.0) < 0.05
    assert abs(sqrt(9.0, 0.01) - 3.0) < 0.05
'''
    )
}

# ─── 15 HOLDOUT PROGRAMS ─────────────────────────────────────────────────────

HOLDOUT_DATA = {
    "bucketsort": (
'''def bucketsort(arr: list, k: int) -> list:
    counts = [0] * k
    for x in arr:
        counts[x] += 1
    sorted_arr = []
    # Bug: appends count instead of index i
    for i, count in enumerate(counts):
        sorted_arr.extend([count] * count)
    return sorted_arr
''',
'''import pytest
from programs.bucketsort import bucketsort

def test_bucketsort():
    assert bucketsort([3, 1, 1, 2], 4) == [1, 1, 2, 3]
    assert bucketsort([0, 2, 1], 3) == [0, 1, 2]
'''
    ),
    "find_first_in_sorted": (
'''def find_first_in_sorted(arr: list, x: int) -> int:
    lo = 0
    hi = len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if x == arr[mid] and (mid == 0 or x != arr[mid - 1]):
            return mid
        elif x <= arr[mid]:
            hi = mid
        else:
            # Bug: lo = mid causes infinite loop when lo + 1 == hi
            lo = mid
    return -1
''',
'''import pytest
from programs.find_first_in_sorted import find_first_in_sorted

def test_find_first_in_sorted():
    assert find_first_in_sorted([1, 2, 2, 3], 2) == 1
    assert find_first_in_sorted([1, 2, 3, 4], 5) == -1
    assert find_first_in_sorted([2, 2, 2], 2) == 0
'''
    ),
    "find_in_sorted": (
'''def find_in_sorted(arr: list, x: int) -> int:
    def binsearch(start: int, end: int) -> int:
        if start == end:
            return -1
        mid = start + (end - start) // 2
        if x < arr[mid]:
            return binsearch(start, mid)
        elif x > arr[mid]:
            # Bug: passes mid instead of mid + 1
            return binsearch(mid, end)
        else:
            return mid

    return binsearch(0, len(arr))
''',
'''import pytest
from programs.find_in_sorted import find_in_sorted

def test_find_in_sorted():
    assert find_in_sorted([1, 3, 5, 7], 5) == 2
    assert find_in_sorted([1, 3, 5, 7], 2) == -1
'''
    ),
    "flatten": (
'''def flatten(nested: list) -> list:
    result = []
    for x in nested:
        if isinstance(x, list):
            # Bug: returns instead of extending
            return result + flatten(x)
        else:
            result.append(x)
    return result
''',
'''import pytest
from programs.flatten import flatten

def test_flatten():
    assert flatten([[1, [2]], 3]) == [1, 2, 3]
    assert flatten([1, 2, 3]) == [1, 2, 3]
'''
    ),
    "get_factors": (
'''def get_factors(n: int) -> list:
    if n == 1:
        return []
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            # Bug: recurses on n instead of n // i
            return [i] + get_factors(n)
    return [n]
''',
'''import pytest
from programs.get_factors import get_factors

def test_get_factors():
    assert get_factors(12) == [2, 2, 3]
    assert get_factors(7) == [7]
'''
    ),
    "kheapsort": (
'''import heapq

def kheapsort(arr: list, k: int) -> list:
    heap = arr[:k]
    heapq.heapify(heap)
    output = []
    # Bug: does not include element from arr[k:] before popping
    for x in arr[k:]:
        output.append(heapq.heappushpop(heap, x))
    while heap:
        output.append(heapq.heappop(heap))
    return output
''',
'''import pytest
from programs.kheapsort import kheapsort

def test_kheapsort():
    assert kheapsort([3, 2, 1, 5, 4], 2) == [1, 2, 3, 4, 5]
'''
    ),
    "knapsack": (
'''def knapsack(capacity: int, items: list) -> int:
    memo = {}
    for i in range(len(items) + 1):
        for w in range(capacity + 1):
            if i == 0 or w == 0:
                memo[i, w] = 0
            else:
                weight, value = items[i - 1]
                # Bug: strict inequality > instead of <= ignores capacity
                if weight < w:
                    memo[i, w] = max(memo[i - 1, w], value + memo[i - 1, w - weight])
                else:
                    memo[i, w] = memo[i - 1, w]
    return memo[len(items), capacity]
''',
'''import pytest
from programs.knapsack import knapsack

def test_knapsack():
    assert knapsack(10, [(3, 2), (4, 3), (5, 4)]) == 7
'''
    ),
    "kth": (
'''def kth(arr: list, k: int) -> int:
    pivot = arr[0]
    below = [x for x in arr[1:] if x < pivot]
    above = [x for x in arr[1:] if x > pivot]
    num_less = len(below)
    num_less_or_equal = len(arr) - len(above)

    if k < num_less:
        return kth(below, k)
    elif k >= num_less_or_equal:
        # Bug: fails to adjust k by the eliminated lower partition
        return kth(above, k)
    else:
        return pivot
''',
'''import pytest
from programs.kth import kth

def test_kth():
    assert kth([4, 2, 5, 8, 1], 2) == 4
    assert kth([1, 2, 3, 4, 5], 0) == 1
'''
    ),
    "levenshtein": (
'''def levenshtein(source: str, target: str) -> int:
    if source == "" or target == "":
        return len(source) or len(target)
    elif source[0] == target[0]:
        return 1 + levenshtein(source[1:], target[1:])
    else:
        # Bug: missing deletion / insertion comparison branches
        return 1 + levenshtein(source[1:], target[1:])
''',
'''import pytest
from programs.levenshtein import levenshtein

def test_levenshtein():
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("rosettacode", "raisethysword") == 8
'''
    ),
    "lis": (
'''def lis(arr: list) -> int:
    ends = {}
    longest = 0
    for i, val in enumerate(arr):
        prefix_lengths = [length for length in range(1, longest + 1) if arr[ends[length]] < val]
        length = max(prefix_lengths) if prefix_lengths else 0
        if length == longest or val < arr[ends[length + 1]]:
            ends[length + 1] = i
            # Bug: fails to update longest when length + 1 > longest
            longest = length + 1
    return longest
''',
'''import pytest
from programs.lis import lis

def test_lis():
    assert lis([10, 22, 9, 33, 21, 50, 41, 60]) == 5
    assert lis([3, 10, 2, 1, 20]) == 3
'''
    ),
    "mergesort": (
'''def mergesort(arr: list) -> list:
    def merge(left: list, right: list) -> list:
        result = []
        i = j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        result.extend(left[i:])
        result.extend(right[j:])
        return result

    # Bug: checks len(arr) == 0 instead of len(arr) <= 1, infinite recursion on len 1
    if len(arr) == 0:
        return arr
    mid = len(arr) // 2
    left = mergesort(arr[:mid])
    right = mergesort(arr[mid:])
    return merge(left, right)
''',
'''import pytest
from programs.mergesort import mergesort

def test_mergesort():
    assert mergesort([5, 2, 4, 1]) == [1, 2, 4, 5]
    assert mergesort([3, 1]) == [1, 3]
'''
    ),
    "pascal": (
'''def pascal(n: int) -> list:
    rows = [[1]]
    for r in range(1, n):
        row = []
        # Bug: starts range at 0 instead of computing combination
        for c in range(0, r):
            upleft = rows[r - 1][c - 1] if c > 0 else 0
            upright = rows[r - 1][c] if c < r else 0
            row.append(upleft + upright)
        rows.append(row)
    return rows
''',
'''import pytest
from programs.pascal import pascal

def test_pascal():
    assert pascal(4) == [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1]]
'''
    ),
    "quicksort": (
'''def quicksort(arr: list) -> list:
    if not arr:
        return []
    pivot = arr[0]
    lesser = [x for x in arr[1:] if x < pivot]
    # Bug: strictly greater than pivot discards duplicate elements equal to pivot!
    greater = [x for x in arr[1:] if x > pivot]
    return quicksort(lesser) + [pivot] + quicksort(greater)
''',
'''import pytest
from programs.quicksort import quicksort

def test_quicksort():
    assert quicksort([3, 1, 4, 1, 5, 9, 2, 6]) == [1, 1, 2, 3, 4, 5, 6, 9]
    assert quicksort([2, 2, 2]) == [2, 2, 2]
'''
    ),
    "rpn_eval": (
'''def rpn_eval(tokens: list) -> float:
    ops = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a / b
    }
    stack = []
    for token in tokens:
        if isinstance(token, (int, float)):
            stack.append(token)
        elif token in ops:
            b = stack.pop()
            a = stack.pop()
            # Bug: inverts argument order for non-commutative operations!
            stack.append(ops[token](b, a))
    return stack.pop()
''',
'''import pytest
from programs.rpn_eval import rpn_eval

def test_rpn_eval():
    assert rpn_eval([5, 2, "-"]) == 3
    assert rpn_eval([10, 2, "/"]) == 5
'''
    ),
    "sieve": (
'''def sieve(max_n: int) -> list:
    primes = []
    for n in range(2, max_n + 1):
        # Bug: uses any instead of all!
        if any(n % p > 0 for p in primes):
            primes.append(n)
        elif not primes:
            primes.append(n)
    return primes
''',
'''import pytest
from programs.sieve import sieve

def test_sieve():
    assert sieve(20) == [2, 3, 5, 7, 11, 13, 17, 19]
'''
    )
}


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def setup():
    split_manifest = {
        "train": {},
        "holdout": {}
    }

    # Write Train
    for name, (code, test) in TRAIN_DATA.items():
        p_path = PROGRAMS_DIR / f"{name}.py"
        t_path = TESTS_DIR / f"test_{name}.py"
        p_path.write_text(code, encoding="utf-8")
        t_path.write_text(test, encoding="utf-8")
        split_manifest["train"][name] = {
            "program_sha256": compute_sha256(code),
            "test_sha256": compute_sha256(test)
        }

    # Write Holdout
    for name, (code, test) in HOLDOUT_DATA.items():
        p_path = PROGRAMS_DIR / f"{name}.py"
        t_path = TESTS_DIR / f"test_{name}.py"
        p_path.write_text(code, encoding="utf-8")
        t_path.write_text(test, encoding="utf-8")
        split_manifest["holdout"][name] = {
            "program_sha256": compute_sha256(code),
            "test_sha256": compute_sha256(test)
        }

    manifest_path = BASE_DIR / "split_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(split_manifest, f, indent=2)

    print(f"QuixBugs setup complete:")
    print(f"- 5 Train programs written & hashed.")
    print(f"- 15 Holdout programs written & hashed.")
    print(f"- Manifest written to: {manifest_path}")


if __name__ == "__main__":
    setup()
