def pascal(n: int) -> list:
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
