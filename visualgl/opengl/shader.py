import enum

import OpenGL.GL as gl


# TODO: Need to handle other types of shaders I'm sure.
class ShaderType(enum.Enum):
    VERTEX = gl.GL_VERTEX_SHADER
    FRAGMENT = gl.GL_FRAGMENT_SHADER
    # TODO: Add GEOMETRY and see what happens.


class Shader:
    def __init__(self, shader_type: ShaderType, full_source: str, version: int = 430) -> None:
        self.id = gl.glCreateShader(shader_type.value)

        self.compile_shader(shader_type.name, full_source, version)

    def __del__(self):
        gl.glDeleteShader(self.id)

    def compile_shader(self, shader_type: str, full_source: str, version: int) -> None:
        version_str = f"#version {version}"
        define_str = f"#define {shader_type}"

        gl.glShaderSource(self.id, "\n".join([version_str, define_str, full_source]))

        gl.glCompileShader(self.id)

        if gl.glGetShaderiv(self.id, gl.GL_COMPILE_STATUS) != gl.GL_TRUE:
            msg = gl.glGetShaderInfoLog(self.id).decode("unicode_escape")
            raise RuntimeError(f"Shader compilation failed: {msg}")
