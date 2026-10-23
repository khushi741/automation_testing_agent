def lis(arr: list) -> int:
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
