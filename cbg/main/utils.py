import math


def conventional_round(value):
    """
    Conventional rounding: 0.5 and up round up, under 0.5 round down.
    This is different from Python's built-in round() which uses banker's rounding.
    """
    return math.floor(value + 0.5)