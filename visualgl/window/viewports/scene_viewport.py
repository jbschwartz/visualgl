from spatial3d import Vector3

from visualgl.window import InputEvent, InputEventType

from ...camera.camera_controller import CameraController
from ...messaging.event import Event
from ...messaging.listener import listen, listener
from ...scene import Scene
from ..viewport import Viewport


@listener
class SceneViewport(Viewport):
    def __init__(self, scene: Scene, camera: CameraController = None):
        super().__init__()

        self.scene = scene
        self.camera = camera

    def on_event(self, event: InputEvent) -> None:
        """Respond to the provided input event.

        Called by the InputHandler when raw mouse and keyboard events are captured on the window.
        """
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

    @listen(Event.START_RENDERER)
    def on_start(self) -> None:
        self.camera.view("view_iso")

    def on_reflow(self, _position: Vector3, _size: Vector3) -> None:
        self.camera.window_resize(*self.size.xy)
