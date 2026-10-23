def levenshtein(source: str, target: str) -> int:
    if source == "" or target == "":
        return len(source) or len(target)
    elif source[0] == target[0]:
        return 1 + levenshtein(source[1:], target[1:])
    else:
        # Bug: missing deletion / insertion comparison branches
        return 1 + levenshtein(source[1:], target[1:])
