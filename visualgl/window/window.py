from functools import cached_property
from typing import List, Optional

import glfw
from spatial3d import Vector3

from visualgl.messaging.emitter import emitter
from visualgl.messaging.event import Event
from visualgl.settings import settings
from visualgl.timer import Timer

from .exceptions import WindowError
from .input_event import InputEvent, InputEventType
from .layout import Layout
from .layouts.grid import Grid
from .viewport import Viewport


# Pylint cannot resolve the `emit` method since it is provided by the `emitter` decorator.
# pylint: disable=no-member
@emitter
class Window:
    """A GUI window and OpenGL context."""

    def __init__(self, title: str, **kwargs):
        if not glfw.init():
            raise WindowError(self._detail_error("GLFW initialization failed"))

        self._window_hints()
        self.glfw_window = self._create_window(title, kwargs.get("width"), kwargs.get("height"))

        # Get the layout type used (and any arguments for its creation) in a tuple. Default to a
        # one cell grid if nothing is provided. Note that the layout is not created until the
        # `Window.layout` function is called with the constructed Viewports.
        self._layout_type, self._layout_arguments = kwargs.get("layout", (Grid, []))
        self.layout: Optional[Layout] = None

    @cached_property
    def size(self) -> Vector3:
        """Return a Vector3 containing the current size of the window.

        The third component of the vector is always set to 0.
        """
        return Vector3(*glfw.get_window_size(self.glfw_window))

    def assign_viewports(self, viewports: List[Viewport]) -> None:
        """Assign the viewports to the window's layout.

        This function constructs the Layout object.
        """
        self.layout = self._layout_type(viewports, *self._layout_arguments)

    def event(self, event: InputEvent) -> None:
        """Respond to the provided input event.

        Called by the InputHandler when raw mouse and keyboard events are captured on the window.
        """
        # Convert GLFW's content coordinate system (where Y runs from the top of the screen to the
        # bottom) to OpenGL's `glViewport` screen space (where Y runs from the bottom of the screen
        # to the top).
        if event.cursor_position:
            event.cursor_position.y = self.size.y - event.cursor_position.y

        if event.event_type is InputEventType.RESIZE:
            # Invalidate the cached window size now that the window has changed.
            if self.size:
                del self.size
            # Inform the layout that the window has changed so that viewports can also be scaled.
            self.layout.resize(event.size)
        else:
            self.layout.event(event)

    def run(self, fps_limit: Optional[int] = None) -> None:
        """Run the main event loop.

        If `fps_limit` is provided, the loop will execute no faster than the provide value.
        """
        self.layout.resize(self.size)

        period = (1 / fps_limit) if fps_limit else 0

        update = Timer()
        frame = Timer(period=period)

        self.emit(Event.START_RENDERER)

        while not glfw.window_should_close(self.glfw_window):
            with update:
                self.emit(Event.UPDATE, delta=update.time_since_last)

            with frame:
                if frame.ready:
                    self.emit(Event.START_FRAME)
                    self.emit(Event.DRAW)

            glfw.swap_buffers(self.glfw_window)
            glfw.poll_events()

        # Update and write the window settings. This will be used by the next session.
        settings.window.update(
            {
                "width": self.size.x,
                "height": self.size.y,
                "position": glfw.get_window_pos(self.glfw_window),
            }
        )

        settings.write()

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

    def _window_hints(self) -> None:
        """Set window hints."""
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
        glfw.window_hint(glfw.RESIZABLE, True)
        glfw.window_hint(glfw.SAMPLES, 4)
