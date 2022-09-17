from typing import Tuple

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

    @listen(Event.START_RENDERER)
    def on_start(self) -> None:
        self.camera.view("view_iso")

    def on_reflow(self, position: Tuple[int, int], size: Tuple[int, int]) -> None:
        self.camera.window_resize(*self.size)
