import logging
from collections import namedtuple
from typing import Callable, Iterable

import OpenGL.GL as gl

from .opengl.buffer import Buffer
from .opengl.shader import ShaderType
from .opengl.shader_program import ShaderProgram
from .opengl.uniform_buffer import Mapping, UniformBuffer

Entity = namedtuple("Entity", "name shader draw_mode buffer instances per_instance add_children")

logger = logging.getLogger(__name__)


class Renderer:
    def __init__(self, window):
        self.window = window
        self.entities = {}
        self.shaders = {}
        self.ubos = [UniformBuffer("Matrices", 1), UniformBuffer("Light", 2)]

    def start(self) -> None:
        self.configure_opengl()
        self.bind_buffer_objects()
        self.load_buffers()

    def configure_opengl(self) -> None:
        gl.glClearColor(1, 1, 1, 1)

        capabilities = [gl.GL_DEPTH_TEST, gl.GL_MULTISAMPLE, gl.GL_BLEND, gl.GL_CULL_FACE]
        for capability in capabilities:
            gl.glEnable(capability)

        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glCullFace(gl.GL_BACK)
        gl.glFrontFace(gl.GL_CCW)

    def bind_buffer_objects(self) -> None:
        for ubo in self.ubos:
            for shader in self.shaders.values():
                shader.bind_ubo(ubo)

    def load_buffers(self):
        for entity in self.entities.values():
            if len(entity.instances) == 0:
                logger.warning("Entity `%s` has no instances", entity.name)

            if not entity.buffer.is_procedural:
                entity.buffer.set_attribute_locations(entity.shader)
                entity.buffer.load()

    def frame(self):
        # pylint: disable=unsupported-binary-operation
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        self.load_buffer_objects()

    def load_buffer_objects(self):
        for ubo in self.ubos:
            ubo.load()

    def draw(self, window):
        for viewport in window.layout:
            with viewport:
                self.ubos[0].bind(
                    Mapping(viewport.camera.camera, ["projection.matrix", "world_to_camera"])
                )

                self.ubos[1].bind(Mapping(viewport.scene.light, ["position", "color", "intensity"]))

                self.load_buffer_objects()

                for entity in self.entities.values():
                    with entity.shader as shader:
                        with entity.buffer as buffer:
                            for instance, kwargs in entity.instances:
                                entity.per_instance(instance, shader, **kwargs)

                                gl.glDrawArrays(entity.draw_mode, 0, len(buffer))

    def initialize_shader(self, shader_name: str, shader_dir: str) -> None:
        if shader_name in self.shaders:
            return

        try:
            self.shaders[shader_name] = ShaderProgram.from_file_name(shader_name, shader_dir)
        except FileNotFoundError:
            # Single file not found. Instead look for individual files.
            def abbreviation(type_name: str) -> str:
                return type_name[0].lower()

            file_names = {
                shader_type: f"{shader_name}_{abbreviation(shader_type.name)}"
                for shader_type in ShaderType
            }

            try:
                self.shaders[shader_name] = ShaderProgram.from_file_names(
                    shader_name, file_names, shader_dir
                )
            except FileNotFoundError:
                logger.error("Shader program `%s` not found", shader_name)
                raise

    def register_entity_type(
        self,
        name: str,
        buffer: Buffer,
        per_instance: Callable,
        add_children: Callable = None,
        shader_name: str = None,
        shader_dir: str = None,
        draw_mode: int = None,
    ) -> None:
        if self.entities.get(name, None) is not None:
            logger.warning("Entity type `%s` already registered. Keeping original values", name)
            return

        # If shader name is not provided, assume it is the same name as the entity
        shader_name = shader_name or name

        try:
            self.initialize_shader(shader_name, shader_dir)
        except FileNotFoundError:
            logger.error("Entity type `%s` creation failed", name)
            return

        self.entities[name] = Entity(
            name=name,
            shader=self.shaders.get(shader_name),
            draw_mode=draw_mode or gl.GL_TRIANGLES,
            buffer=buffer,
            instances=[],
            per_instance=per_instance,
            add_children=add_children,
        )

    def add(self, entity_type: str, instance, parent=None, **kwargs) -> None:
        entity = self.entities.get(entity_type, None)
        if entity is None:
            logger.error("No entity type `%s` found when adding entity", entity_type)
            return

        entity.instances.append((instance, kwargs))

        if entity.add_children is not None:
            entity.add_children(self, instance)

    def add_many(self, entity_type: str, instances: Iterable, parent=None, **kwargs) -> None:
        if entity_type not in self.entities:
            logger.error("No entity type `%s` found when adding entity", entity_type)
            return

        for index, instance in enumerate(instances):
            # Keyword arguments are provided as iterables, one for each instance in instances
            # For the nth instance, collect all of the nth keyword argument values
            # Ignore keyword arguments if they are not provided or explicitly `None`
            per_instance_kwargs = {
                k: v[index] for k, v in kwargs.items() if index < len(v) and v[index] is not None
            }

            self.add(entity_type, instance, parent, **per_instance_kwargs)
