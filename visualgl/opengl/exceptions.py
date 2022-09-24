from typing import Iterable

from visualgl.exceptions import VisualError


class OpenGLError(VisualError):
    """Raised for OpenGL related errors."""


class UniformArraySizeError(OpenGLError):
    def __init__(self, got_number: int, expected_number: int, expected_types: Iterable[type]):
        try:
            expected_type_string = ", ".join(
                [f"`{expected.__name__}`" for expected in expected_types]
            )
        except TypeError:
            expected_type_string = expected_types.__name__

        super().__init__(
            f"Expected {expected_number} {expected_type_string}(s), got {got_number} instead."
        )


class UniformSizeError(OpenGLError):
    pass


class UniformTypeError(OpenGLError):
    def __init__(self, got_type: type, expected_types: Iterable[type]):
        try:
            expected_type_string = ", ".join(
                [f"`{expected.__name__}`" for expected in expected_types]
            )
        except TypeError:
            expected_type_string = expected_types.__name__

        super().__init__(
            f"Unexpected Uniform value type `{got_type.__name__}` (expected {expected_type_string})"
        )
