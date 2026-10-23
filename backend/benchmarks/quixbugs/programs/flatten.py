def flatten(nested: list) -> list:
    result = []
    for x in nested:
        if isinstance(x, list):
            # Bug: returns instead of extending
            return result + flatten(x)
        else:
            result.append(x)
    return result
