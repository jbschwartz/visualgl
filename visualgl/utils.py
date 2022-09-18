from numbers import Number
from typing import Union


def raise_if(should_raise: bool, exception_type: Exception):
    if should_raise:
        raise exception_type


def sign(value: Number) -> Union[None, int]:
    if value < 0:
        return -1
    elif value > 0:
        return 1
    elif value == 0:
        return 0
    else:
        return None
