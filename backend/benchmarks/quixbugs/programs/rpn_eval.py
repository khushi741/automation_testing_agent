def rpn_eval(tokens: list) -> float:
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
