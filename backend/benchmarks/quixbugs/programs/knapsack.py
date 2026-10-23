def knapsack(capacity: int, items: list) -> int:
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
