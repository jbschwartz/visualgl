import json
import math

import OpenGL.GL as gl
from spatial import Matrix4, Vector3

from visual import Camera, Window
from visual.opengl.buffer import Buffer
from visual.opengl.shader_program import ShaderProgram
from visual.opengl.uniform_buffer import Mapping, UniformBuffer

from .ambient_light import AmbientLight
from .bindings import Bindings
from .camera_controller import CameraController, CameraSettings
from .renderer import Renderer
from .simulation import Simulation


def triangle(
    camera: Camera, sp: ShaderProgram, scale: float = 1.0, opacity: float = 0.5, color=None
):
    if not hasattr(camera, "target"):
        return

    color = color or [0, 0.5, 1]

    # TODO: Hacky. See the TODO in Camera about the target attribute
    # Ultimately would like to see a vector passed (instead of camera)
    model = Matrix4(
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, camera.target.x, camera.target.y, camera.target.z, 1]
    )

    sp.uniforms.model_matrix = model
    sp.uniforms.scale_matrix = Matrix4([scale, 0, 0, 0, 0, scale, 0, 0, 0, 0, scale, 0, 0, 0, 0, 1])

    sp.uniforms.color_in = color
    sp.uniforms.in_opacity = opacity


def grid(placeholder, sp: ShaderProgram, scale: float = 1.0):
    sp.uniforms.scale_matrix = Matrix4([scale, 0, 0, 0, 0, scale, 0, 0, 0, 0, scale, 0, 0, 0, 0, 1])


if __name__ == "__main__":
    window = Window(750, 750, "Visual")

    sim = Simulation()

    triangle_buffer = Buffer.from_points(
        [Vector3(0.5, -0.33, 0), Vector3(0.0, 0.66, 0), Vector3(-0.5, -0.33, 0)]
    )

    grid_buffer = Buffer.from_points(
        [
            Vector3(
                0.5,
                0.5,
                0,
            ),
            Vector3(
                -0.5,
                0.5,
                0,
            ),
            Vector3(
                -0.5,
                -0.5,
                0,
            ),
            Vector3(
                -0.5,
                -0.5,
                0,
            ),
            Vector3(
                0.5,
                -0.5,
                0,
            ),
            Vector3(
                0.5,
                0.5,
                0,
            ),
        ]
    )

    camera = Camera(Vector3(0, -1250, 375), Vector3(0, 0, 350), Vector3(0, 0, 1))
    light = AmbientLight(Vector3(0, -750, 350), Vector3(1, 1, 1), 0.3)
    renderer = Renderer(camera, light)

    renderer.register_entity_type(
        name="triangle", shader_name="billboard", buffer=triangle_buffer, per_instance=triangle
    )

    renderer.register_entity_type(name="grid", buffer=grid_buffer, per_instance=grid)

    renderer.add("triangle", camera, None, scale=20)

    renderer.add("grid", None, None, scale=10000)

    bindings = Bindings()
    settings = CameraSettings()
    camera_controller = CameraController(camera, settings, bindings, sim, window)

    matrix_ub = UniformBuffer("Matrices", 1)

    matrix_ub.bind(Mapping(camera, ["projection.matrix", "world_to_camera"]))

    light_ub = UniformBuffer("Light", 2)

    light_ub.bind(Mapping(light, ["position", "color", "intensity"]))

    renderer.ubos = [matrix_ub, light_ub]

    window.run(fps_limit=60)
