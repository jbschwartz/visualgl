from numbers import Number
from typing import Union

import glfw


def glfw_detail_error(message: str) -> str:
    """Return a detailed GLFW error message if possible. Otherwise return the provided `message`."""
    code, description = glfw.get_error()

    error_string = message

    if description is not None:
        error_string += f": {description}"

    if code != 0:
        error_string += f" (code {code})"

    return error_string


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
