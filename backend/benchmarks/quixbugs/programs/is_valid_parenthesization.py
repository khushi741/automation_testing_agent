def is_valid_parenthesization(parens: str) -> bool:
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
