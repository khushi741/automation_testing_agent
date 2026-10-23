def bucketsort(arr: list, k: int) -> list:
    counts = [0] * k
    for x in arr:
        counts[x] += 1
    sorted_arr = []
    # Bug: appends count instead of index i
    for i, count in enumerate(counts):
        sorted_arr.extend([count] * count)
    return sorted_arr
