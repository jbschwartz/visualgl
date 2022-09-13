from typing import Optional

import glfw
from OpenGL.GL import GL_TRUE
from spatial3d import Vector3

from visualgl.exceptions import WindowError

from .messaging.emitter import emitter
from .messaging.event import Event
from .settings import settings
from .timer import Timer
from .utils import sign


def _callback(function):
    """Decorator to indicate that the method is a GLFW callback function."""
    # pylint: disable=protected-access
    # Use a protected attribute so as not to disturb any aspects of the function.
    function._callback = getattr(glfw, f"set_{function.__name__.lstrip('_')}_callback")
    return function


# Pylint cannot resolve the `emit` method since it is provided by the `emitter` decorator.
# pylint: disable=no-member
@emitter
class Window:
    """A GUI window and OpenGL context."""

    def __init__(self, title: str, **kwargs):
        if not glfw.init():
            raise WindowError(self._detail_error("GLFW initialization failed"))

        self._window_hints()
        self.window = self._create_window(title, kwargs.get("width"), kwargs.get("height"))

        self._set_callbacks()

        # The current mouse button being held down in the window. Use None if no button is pressed.
        # Note: GLFW uses 0 to represent the left mouse button so do not attempt to clear this
        # value by setting to 0. Modifiers do not suffer from this problem.
        self.current_button_down: Optional[int] = None
        # Store the currently held down or released modifiers (e.g., shift). This attribute
        # functions like a bit field with each bit representing a different key.
        self.current_key_modifiers: int = 0

        # The last recorded cursor position in normalized device coordinates.
        self.last_cursor_position: Optional[Vector3] = None

    @property
    def cursor_position(self) -> Vector3:
        """Return a Vector3 containing the current cursor position in normalized device coordinates.

        The third component of the vector is always set to 0.
        """
        return self.ndc(Vector3(*glfw.get_cursor_pos(self.window)))

    @property
    def size(self) -> Vector3:
        """Return a Vector3 containing the current size of the window.

        The third component of the vector is always set to 0.
        """
        return Vector3(*glfw.get_window_size(self.window))

    def ndc(self, cursor_position: Vector3) -> Vector3:
        """Return the normalized device coordinates at the provided cursor position in pixels.

        Normalize device coordinates are a resolution-independent coordinate system. The bottom left
        corner is (-1, -1). The top right corner is (1, 1). The center of the screen is (0, 0).

        The third component of the vector is always set to 0.
        """
        return Vector3(
            2 * cursor_position.x / self.size.x - 1, 1 - 2 * cursor_position.y / self.size.y
        )

    def run(self, fps_limit: Optional[int] = None) -> None:
        """Run the main event loop.

        If `fps_limit` is provided, the loop will execute no faster than the provide value.
        """
        # Send a window resize event so observers are provided the initial window size
        self._window_size(self.window, self.size.x, self.size.y)

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

        # Update and write the window settings. This will be used by the next session.
        settings.window.update(
            {
                "width": self.size.x,
                "height": self.size.y,
                "position": glfw.get_window_pos(self.window),
            }
        )

        settings.write()

    @_callback
    def _cursor_pos(self, _window, x_position: int, y_position: int) -> None:
        """Emit the cursor position event or drag event if there are pressed mouse buttons."""
        cursor_position_ndc = self.ndc(Vector3(x_position, y_position))

        if self.last_cursor_position is not None:
            cursor_delta = cursor_position_ndc - self.last_cursor_position
        else:
            cursor_delta = Vector3()

        self.last_cursor_position = cursor_position_ndc

        self.emit(
            Event.DRAG if self.current_button_down is not None else Event.CURSOR,
            self.current_button_down,
            cursor_position_ndc,
            cursor_delta,
            self.current_key_modifiers,
        )

    @_callback
    def _key(self, _window, key: int, _scancode, action: int, modifiers: int) -> None:
        """Emit the key event for key presses, releases, and repeats."""
        self.current_key_modifiers = modifiers

        self.emit(Event.KEY, key, action, self.current_key_modifiers)

    @_callback
    def _mouse_button(self, _window, button: int, action: int, modifiers: int) -> None:
        """Emit the click event for clicks and releases."""
        self.emit(Event.CLICK, button, action, self.cursor_position, modifiers)

        # Record which mouse button is being held down. This does not support holding down multiple
        # buttons at once.
        self.current_button_down = button if action == glfw.PRESS else None

    @_callback
    def _scroll(self, _window, x_direction: float, y_direction: float) -> None:
        """Emit the scroll event for both scroll directions."""
        # The scroll amounts are normalized by only passing on their direction.
        self.emit(Event.SCROLL, sign(x_direction), sign(y_direction), self.cursor_position)

    @_callback
    def _window_size(self, _window, width: int, height: int) -> None:
        """Emit the window resize event."""
        self.emit(Event.WINDOW_RESIZE, width, height)

    def _create_window(self, title: str, width: Optional[int] = None, height: Optional[int] = None):
        """Create the window with the provided settings using GLFW."""
        # Try to use the _settings values if they exist. Otherwise rely on defaults.
        width = width if width else settings.window.width
        height = height if height else settings.window.height

        window = glfw.create_window(width, height, title, None, None)

        if not window:
            glfw.terminate()
            raise WindowError(self._detail_error("GLFW create window failed"))

        # Set the position of the window from the _settings session.
        if "position" in settings.window:
            glfw.set_window_pos(window, *settings.window.position)

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

    def _set_callbacks(self):
        """Look for all decorated methods on Window and set them as GLFW callbacks."""
        for name in dir(self):
            method = getattr(self, name)
            if setter := getattr(method, "_callback", None):
                setter(self.window, method)

    def _window_hints(self) -> None:
        """Set window hints."""
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
        glfw.window_hint(glfw.RESIZABLE, GL_TRUE)
        glfw.window_hint(glfw.SAMPLES, 4)
