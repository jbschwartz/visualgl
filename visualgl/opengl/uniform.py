import logging
from typing import Callable

import OpenGL.GL as gl

from visualgl.opengl import decorators

from .exceptions import UniformArraySizeError, UniformSizeError, UniformTypeError

logger = logging.getLogger(__name__)

gl.GL_TYPE_UNIFORM_FN = {
    gl.GL_INT: decorators.primitive(gl.glUniform1iv, int),
    gl.GL_FLOAT: decorators.primitive(gl.glUniform1fv, float),
    gl.GL_BOOL: decorators.primitive(gl.glUniform1iv, bool),
    gl.GL_FLOAT_VEC3: decorators.vector(gl.glUniform3fv, 3),
    gl.GL_FLOAT_MAT4: decorators.matrix(gl.glUniformMatrix4fv, 4),
    gl.GL_SAMPLER_2D: None,
}


def setter_factory(gl_type: int, array_size: int) -> Callable:
    array_decorator = gl.GL_TYPE_UNIFORM_FN.get(gl_type, None)

    if array_decorator is not None:
        return array_decorator(array_size)

    return None


class Uniform:
    def __init__(self, name: str, location: int, set_value: Callable) -> None:
        self.name = name
        self.location = location
        self.set_value = set_value
        self._value = None

        self.logged = {}

    @classmethod
    def from_program_index(cls, program_id: int, index: int) -> "Uniform":
        """Construct a Uniform from the shader program id and the Uniform index."""
        # properties = [gl.GL_TYPE, gl.GL_NAME_LENGTH, gl.GL_LOCATION, gl.GL_ARRAY_SIZE]

        name, array_size, gl.GL_type = gl.glGetActiveUniform(program_id, index)
        name = name.decode("ascii").rstrip("[0]")
        location = gl.glGetUniformLocation(program_id, name)
        # gl.GL_type, name_length, location, array_size = gl.glGetProgramResourceiv(
        #   program_id,
        #   gl.GL_UNIFORM,
        #   index,
        #   len(properties),
        #   properties,
        #   len(properties)
        # )

        # name_length = len(name)

        # Returns a list of ascii values including NUL terminator and [0] for uniform arrays
        # name_ascii = gl.glGetProgramResourceName(program_id, gl.GL_UNIFORM, index, name_length)

        # Format the name as a useful string
        # name = ''.join(chr(c) for c in name_ascii).strip('\x00').strip('[0]')

        try:
            set_value = setter_factory(gl.GL_type, array_size)
        except KeyError as e:
            raise KeyError(f"For {name}, unknown uniform type: {gl.GL_type}") from e

        return cls(name, location, set_value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.set_value is None:
            logger.error("Setting a value on unsettable Uniform %s", self.name)
            return

        self._value = value
        try:
            self.set_value(self.location, value)
        except (UniformArraySizeError, UniformSizeError, UniformTypeError) as e:
            if self.logged.get(type(e), None) is None:
                self.logged[type(e)] = True
                logger.error("When setting `%s` uniform: %s", self.name, e.args[0])
