import logging
import os

from .ambient_light import AmbientLight
from .camera.camera import Camera
from .camera.camera_controller import CameraController, CameraSettings
from .filetypes.stl.stl_parser import STLParser
from .frozen_dict import FrozenDict
from .renderer import Renderer
from .settings import settings
from .window import Window

logging.getLogger(__name__).addHandler(logging.NullHandler())


def settings_directory(path: str) -> None:
    """Setup a settings directory at the provided path."""
    try:
        os.makedirs(path)
    except FileExistsError:
        pass

    settings["directory"] = path
