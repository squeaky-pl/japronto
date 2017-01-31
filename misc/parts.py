from functools import partial
import types
import math


def make_parts(value, get_size, dir=1):
    parts = []

    left = bytearray(value)
    while left:
        if isinstance(get_size, types.GeneratorType):
            size = next(get_size)
        else:
            size = get_size

        if dir == 1:
            parts.append(bytes(left[:size]))
            left = left[size:]
        else:
            parts.append(bytes(left[-size:]))
            left = left[:-size]

    return parts if dir == 1 else list(reversed(parts))


def one_part(value):
    return [value]


def geometric_series():
    s = 2
    while 1:
        yield s
        s *= 2


def fancy_series(minimum=2):
    x = 0
    while 1:
        yield int(minimum + abs(math.sin(x / 3)) * 64)
        x += 1
