import weakref
from functools import cached_property
from typing import List, Optional

import glfw
from spatial3d import Vector3

from visualgl.settings import settings
from visualgl.utils import glfw_detail_error

from .exceptions import WindowError
from .input_event import InputEvent, InputEventType
from .layout import Layout
from .layouts.grid import Grid
from .viewport import Viewport


class Window:
    """A GUI window and OpenGL context."""

    def __init__(self, title: str, **kwargs):
        self._window_hints()
        self.glfw_window = self._create_window(title, kwargs.get("width"), kwargs.get("height"))

        # Get the layout type used (and any arguments for its creation) in a tuple. Default to a
        # one cell grid if nothing is provided. Note that the layout is not created until the
        # `Window.layout` function is called with the constructed Viewports.
        self._layout_type, self._layout_arguments = kwargs.get("layout", (Grid, []))
        self.layout: Optional[Layout] = None

        self._finalizer = weakref.finalize(self, self._update_settings)

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
        self.layout.resize(self.size)

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

    def _create_window(self, title: str, width: Optional[int] = None, height: Optional[int] = None):
        """Create the window with the provided settings using GLFW."""
        # Try to use the _settings values if they exist. Otherwise rely on defaults.
        width = width if width else settings.window.width
        height = height if height else settings.window.height

        window = glfw.create_window(width, height, title, None, None)

        if not window:
            glfw.terminate()
            raise WindowError(glfw_detail_error("GLFW create window failed"))

        # Set the position of the window from the _settings session.
        if "position" in settings.window:
            glfw.set_window_pos(window, *settings.window.position)

        glfw.make_context_current(window)
        glfw.swap_interval(0)

        return window

    def _update_settings(self) -> None:
        """Update and write the window settings.

        This information saved wil be used by the next session.
        """
        settings.window.update(
            {
                "width": self.size.x,
                "height": self.size.y,
                "position": glfw.get_window_pos(self.glfw_window),
            }
        )

        settings.write()

    def _window_hints(self) -> None:
        """Set window hints."""
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
        glfw.window_hint(glfw.RESIZABLE, True)
        glfw.window_hint(glfw.SAMPLES, 4)
