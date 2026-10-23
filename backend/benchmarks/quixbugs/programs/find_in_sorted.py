def find_in_sorted(arr: list, x: int) -> int:
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
