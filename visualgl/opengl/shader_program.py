import logging
from typing import Any
import os
from typing import Iterable

import OpenGL.GL as gl

from ..utils import raise_if
from .shader import Shader, ShaderType
from .uniform import Uniform
from .uniform_buffer import UniformBuffer

logger = logging.getLogger(__name__)


class FrozenDict:
    """Dictionary that does not allow keys to be added to after initialization."""

    def __init__(self, d: dict) -> None:
        for key, value in d.items():
            self.__dict__[key] = value

    def __setattr__(self, name: str, value: Any) -> None:
        if hasattr(self, name):
            self.__dict__[name] = value
        else:
            raise AttributeError


class UniformDict:
    def __init__(self, program_id, d: dict) -> None:
        self.__dict__["program_id"] = program_id
        self.__dict__["_uniforms"] = FrozenDict(d)
        self.__dict__["_already_logged"] = []

    @classmethod
    def from_program(cls, program_id: int) -> "UniformDict":
        uniforms = {}

        num_uniforms = gl.glGetProgramInterfaceiv(program_id, gl.GL_UNIFORM, gl.GL_ACTIVE_RESOURCES)

        for uniform_index in range(num_uniforms):
            uniform = Uniform.from_program_index(program_id, uniform_index)

            uniforms[uniform.name] = uniform

        return cls(program_id, uniforms)

    def __getattr__(self, name):
        return getattr(self._uniforms, name)

    def __setattr__(self, name, value):
        try:
            uniform = getattr(self._uniforms, name)
            uniform.value = value
        except AttributeError:
            if name not in self._already_logged:
                self._already_logged.append(name)
                logger.warning(
                    "Setting uniform '%s' that does not exist in program '%s'",
                    name,
                    self.program_id,
                )


class ShaderProgram:
    DEFAULT_FOLDER = "../glsl/"
    DEFAULT_EXTENSION = ".glsl"

    def __init__(self, name, shaders: Iterable[Shader]) -> None:
        self.id = gl.glCreateProgram()

        #  Used for warning/error messaging
        self.name = name

        logger.debug("Shader program '%s' assigned ID %s", self.name, self.id)

        for shader in shaders:
            gl.glAttachShader(self.id, shader.id)

        self.link()

        self.uniforms = UniformDict.from_program(self.id)

    @classmethod
    def get_shader_file_path(cls) -> str:
        dirname = os.path.dirname(__file__)
        return os.path.join(dirname, cls.DEFAULT_FOLDER)

    @classmethod
    def from_file_name(cls, file_name: str, shader_dir: str) -> "ShaderProgram":
        """Open a glsl file with the given file name and create a ShaderProgram."""
        directory = shader_dir or cls.get_shader_file_path()
        path = os.path.join(directory, file_name + cls.DEFAULT_EXTENSION)
        with open(path) as file:
            source = file.read()

        shaders = [Shader(shader_type, source) for shader_type in ShaderType]

        return cls(file_name, shaders)

    @classmethod
    def from_file_names(
        cls, shader_name: str, file_names_by_type: dict, shader_dir: str
    ) -> "ShaderProgram":
        directory = shader_dir or cls.get_shader_file_path()

        shaders = []
        for shader_type, file_name in file_names_by_type.items():
            path = os.path.join(directory, file_name + cls.DEFAULT_EXTENSION)
            with open(path) as file:
                source = file.read()

            shaders.append(Shader(shader_type, source))

        return cls(shader_name, shaders)

    def __del__(self):
        gl.glDeleteProgram(self.id)

    def __enter__(self) -> "ShaderProgram":
        gl.glUseProgram(self.id)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        gl.glUseProgram(0)

    def link(self):
        gl.glLinkProgram(self.id)

        if gl.glGetProgramiv(self.id, gl.GL_LINK_STATUS) != gl.GL_TRUE:
            msg = gl.glGetProgramInfoLog(self.id).decode("unicode_escape")
            raise RuntimeError(f"Error linking program: {msg}")

    def bind_ubo(self, ubo: UniformBuffer) -> None:
        """Set the program's uniform block to the binding index provided by the Uniform Buffer.

        If the ShaderProgram doesn't use the UniformBuffer, just ignore it.
        """
        block_index = gl.glGetUniformBlockIndex(self.id, ubo.name)

        if block_index != gl.GL_INVALID_INDEX:
            gl.glUniformBlockBinding(self.id, block_index, ubo.binding_index)

    def attribute_location(self, name: str) -> int:
        result = gl.glGetAttribLocation(self.id, name)

        raise_if(result == -1, AttributeError)

        return result
