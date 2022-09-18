from spatial3d import Vector3

from visualgl.camera import CameraController
from visualgl.messaging.event import Event
from visualgl.messaging.listener import listen, listener
from visualgl.scene import Scene

from ..input_event import InputEvent, InputEventType
from ..viewport import Viewport


@listener
class SceneViewport(Viewport):
    """A viewport for displaying a scene (collection of object) with a controllable camera."""

    def __init__(self, scene: Scene, camera: CameraController = None):
        super().__init__()

        self.scene = scene
        self.camera = camera

    def on_event(self, event: InputEvent) -> None:
        """Pass the event onto the Camera."""
        if event.event_type is InputEventType.DRAG:
            self.camera.drag(
                event.button, event.cursor_position, event.cursor_delta, event.modifiers
            )
        elif event.event_type is InputEventType.CLICK:
            self.camera.click(event.button, event.action, event.cursor_position, event.modifiers)
        elif event.event_type is InputEventType.KEY:
            self.camera.key(event.key, event.action, event.modifiers)
        elif event.event_type is InputEventType.SCROLL:
            self.camera.scroll(*event.scroll.xy, event.cursor_position)

    def on_reflow(self, _position: Vector3, _size: Vector3) -> None:
        """Update the camera's aspect ratio when the viewport changes size."""
        self.camera.window_resize(*self.size.xy)

    @listen(Event.START_RENDERER)
    def on_start(self) -> None:
        """Set up the scene and camera when the viewport is first set to render."""
        self.camera.view("view_iso")
