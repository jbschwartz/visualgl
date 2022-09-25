from spatial3d import Vector3

from visualgl.camera import CameraController
from visualgl.scene import Scene

from ..input_event import InputEvent, InputEventType
from ..viewport import Viewport


class SceneViewport(Viewport):
    """A viewport for displaying a scene (collection of object) with a controllable camera."""

    def __init__(self, scene: Scene, camera: CameraController = None):
        super().__init__()

        self.scene = scene
        self.camera = camera or CameraController(self.scene)

    def on_event(self, event: InputEvent) -> None:
        """Pass the event onto the Camera."""
        if event.event_type is InputEventType.CLICK:
            self._update_camera_target(event.cursor_position)
        elif event.command and event.command.controller == "camera":
            self.camera.command(event)

    def on_reflow(self, _position: Vector3, _size: Vector3) -> None:
        """Update the camera's aspect ratio when the viewport changes size."""
        self.camera.update_output_size(self.size)

    def on_start(self) -> None:
        """Set up the scene and camera when the viewport is first set to render."""
        self._initialize_camera()

    def on_update(self, delta: float) -> None:
        """Update the scene with the amount of time elapsed (`delta`)."""
        self.scene.update(delta)

    def _initialize_camera(self) -> None:
        if len(self.scene.entities) > 0:
            self.camera.target = self.scene.aabb.center
        self.camera.view("iso")

    def _update_camera_target(self, cursor_position: Vector3) -> None:
        ray = self.camera.cast_ray(cursor_position)
        intersection = self.scene.intersect(ray)

        if intersection.hit:
            self.camera.target = ray.evaluate(intersection.t)
        else:
            if len(self.scene.entities) > 0:
                self.camera.target = self.scene.aabb.center
            else:
                self.camera.target = Vector3()

        assert self.camera.target is not None, "There must always be a valid camera target."
        assert isinstance(self.camera.target, Vector3), "Camera target must be a Vector3."
