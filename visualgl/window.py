import json
import os
from typing import Any, Dict, Optional

import glfw
from OpenGL.GL import GL_TRUE
from spatial3d import Vector3

from visualgl.exceptions import WindowError

from .messaging.emitter import emitter
from .messaging.event import Event
from .settings import settings
from .timer import Timer
from .utils import sign


@emitter
class Window:
    """A GUI window and OpenGL context."""

    # The default window size used.
    DEFAULT_WINDOW_SIZE = Vector3(1000, 1000)

    # The file name used to store windows settings on disk.
    SETTINGS_FILE_NAME = "window.json"

    def __init__(self, title: str, **kwargs):
        self.dragging = None
        self.modifiers = 0

        if not glfw.init():
            raise WindowError(self._detail_error("GLFW initialization failed"))

        self._window_hints()
        self.window = self._create_window(title, kwargs.get("width"), kwargs.get("height"))

        self.set_callbacks()

        self.last_cursor_position = self.get_cursor()

    def set_callbacks(self):
        glfw.set_window_size_callback(self.window, self.window_callback)
        glfw.set_key_callback(self.window, self.key_callback)
        glfw.set_scroll_callback(self.window, self.scroll_callback)
        glfw.set_mouse_button_callback(self.window, self.mouse_button_callback)
        glfw.set_cursor_pos_callback(self.window, self.cursor_pos_callback)

    def key_callback(self, window, key, scancode, action, mods):
        self.modifiers = mods

        self.emit(Event.KEY, key, action, self.modifiers)

    def scroll_callback(self, window, x_direction, y_direction):
        self.emit(Event.SCROLL, sign(x_direction), sign(y_direction))

    def mouse_button_callback(self, window, button, action, mods):
        self.emit(Event.CLICK, button, action, self.get_cursor(), mods)

        # Record which mouse button is being dragged
        self.dragging = button if action == glfw.PRESS else None

    def cursor_pos_callback(self, window, x, y):
        cursor = Vector3(x, y)

        if self.last_cursor_position:
            # TODO: This is backwards. Needs to be current - previous.
            cursor_delta = self.last_cursor_position - cursor

        self.last_cursor_position = cursor

        event = Event.DRAG if self.dragging is not None else Event.CURSOR
        self.emit(event, self.dragging, cursor, cursor_delta, self.modifiers)

    def window_callback(self, window, width, height):
        self.width = width
        self.height = height
        self.emit(Event.WINDOW_RESIZE, width, height)

    # TODO: Remove this function (in favor of a property?). It's probably not necessary since the cursor_pos callback is constantly updating last_cursor_position
    def get_cursor(self):
        return Vector3(*glfw.get_cursor_pos(self.window), 0)

    def ndc(self, cursor):
        return Vector3(2 * cursor.x / self.width - 1, 1 - 2 * cursor.y / self.height)

    def run(self, fps_limit: Optional[int] = None):
        # Send a window resize event so observers are provided the initial window size
        self.window_callback(self.window, *glfw.get_window_size(self.window))

        period = (1 / fps_limit) if fps_limit else 0

        update = Timer()
        frame = Timer(period=period)

        self.emit(Event.START_RENDERER)

        while not glfw.window_should_close(self.window):
            with update:
                self.emit(Event.UPDATE, delta=update.time_since_last)

            with frame:
                if frame.ready:
                    self.emit(Event.START_FRAME)
                    self.emit(Event.DRAW)

            glfw.swap_buffers(self.window)
            glfw.poll_events()

        self._write_window_settings()

    def _create_window(self, title: str, width: Optional[int] = None, height: Optional[int] = None):
        """Create the window with the provided settings using GLFW."""
        last = self._load_window_settings()

        # Try to use the last values if they exist. Otherwise rely on defaults.
        width = width if width else last.get("width", Window.DEFAULT_WINDOW_SIZE.x)
        height = height if height else last.get("height", Window.DEFAULT_WINDOW_SIZE.y)

        window = glfw.create_window(width, height, title, None, None)

        if not window:
            glfw.terminate()
            raise WindowError(self._detail_error("GLFW create window failed"))

        # Set the position of the window from the last session.
        if "x_position" in last and "y_position" in last:
            glfw.set_window_pos(window, last["x_position"], last["y_position"])

        glfw.make_context_current(window)
        glfw.swap_interval(0)

        return window

    def _detail_error(self, message: str) -> str:
        """Return a detailed error message if possible. Otherwise return the provided `message`."""
        code, description = glfw.get_error()

        error_string = message

        if description is not None:
            error_string += f": {description}"

        if code != 0:
            error_string += f" (code {code})"

        return error_string

    def _load_window_settings(self) -> Dict[str, Any]:
        """Return a dictionary with the window settings (e.g., size and position) from last session.

        If no settings file exists, return an empty dictionary.
        """

        # If the user has not provided a settings directory, there is no file to look for.
        if not (settings_path := self._settings_path()):
            return {}

        try:
            with open(settings_path, encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            # This might be the first time that the window has been opened. A settings file will
            # be saved at the end of the session (see `_write_window_settings`).
            pass

        return {}

    def _settings_path(self) -> Optional[str]:
        """Return the path to the window settings file.

        If the settings directory is not set, return None.
        """
        if not (settings_directory := settings["directory"]):
            return None

        return os.path.join(settings_directory, Window.SETTINGS_FILE_NAME)

    def _window_hints(self) -> None:
        """Set window hints."""
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
        glfw.window_hint(glfw.RESIZABLE, GL_TRUE)
        glfw.window_hint(glfw.SAMPLES, 4)

    def _write_window_settings(self) -> None:
        """Write the current window settings to a file in the settings directory.

        If the settings directory is not set, this function does nothing.
        """
        if not (settings_path := self._settings_path()):
            return

        width, height = glfw.get_window_size(self.window)
        x_position, y_position = glfw.get_window_pos(self.window)
        with open(settings_path, "w", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    {
                        "width": width,
                        "height": height,
                        "x_position": x_position,
                        "y_position": y_position,
                    }
                )
            )
