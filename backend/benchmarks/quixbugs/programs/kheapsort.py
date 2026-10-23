import heapq

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
