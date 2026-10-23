def quicksort(arr: list) -> list:
    if not arr:
        return []
    pivot = arr[0]
    lesser = [x for x in arr[1:] if x < pivot]
    # Bug: strictly greater than pivot discards duplicate elements equal to pivot!
    greater = [x for x in arr[1:] if x > pivot]
    return quicksort(lesser) + [pivot] + quicksort(greater)
