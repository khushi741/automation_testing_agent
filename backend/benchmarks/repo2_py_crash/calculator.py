def calculate_average(scores):
    """
    Computes average of list of numeric scores.
    INTENTIONAL BUG: Crashes with ZeroDivisionError when scores is empty!
    """
    total = sum(scores)
    return total / len(scores)


def get_user_domain(user_record):
    """
    Extracts email domain from user dictionary record.
    INTENTIONAL BUG: Crashes with AttributeError or TypeError when email is None!
    """
    email = user_record.get("email")
    return email.split("@")[1]


def sum_positive_numbers(numbers):
    total = 0
    for n in numbers:
        if n > 0:
            total += n
    return total
