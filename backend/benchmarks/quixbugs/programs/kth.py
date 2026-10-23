def kth(arr: list, k: int) -> int:
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
