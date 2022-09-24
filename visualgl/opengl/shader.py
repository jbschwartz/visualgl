import enum

import OpenGL.GL as gl

from .exceptions import OpenGLError


@enum.unique
class ShaderType(enum.Enum):
    """OpenGL shader types."""

    VERTEX = gl.GL_VERTEX_SHADER
    FRAGMENT = gl.GL_FRAGMENT_SHADER


# pylint: disable=too-few-public-methods
class Shader:
    """OpenGL shader."""

    def __init__(self, shader_type: ShaderType, full_source: str, version: int = 430) -> None:
        self.id = gl.glCreateShader(shader_type.value)

        self._compile_shader(shader_type.name, full_source, version)

    def __del__(self):
        """Release the OpenGL resource when the shader is deleted.

        This will be called even if the compilation fails and an exception is raised.
        """
        gl.glDeleteShader(self.id)

    def _compile_shader(self, shader_type: str, full_source: str, version: int) -> None:
        """Compile the source code of the shader."""
        version_str = f"#version {version}"
        define_str = f"#define {shader_type}"

        gl.glShaderSource(self.id, "\n".join([version_str, define_str, full_source]))

        gl.glCompileShader(self.id)

        # Check if the shader compilation was successful. Raise an exception if not.
        if gl.glGetShaderiv(self.id, gl.GL_COMPILE_STATUS) != gl.GL_TRUE:
            msg = gl.glGetShaderInfoLog(self.id).decode("unicode-escape")
            raise OpenGLError(f"Shader compilation failed: {msg}")
