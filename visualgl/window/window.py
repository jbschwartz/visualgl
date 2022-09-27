import logging
import weakref
from functools import cached_property
from typing import List, Optional, Tuple

import glfw
from spatial3d import Vector3

from visualgl.settings import settings
from visualgl.utils import glfw_detail_error

from .exceptions import WindowError
from .input_event import InputEvent, InputEventType
from .layout import Layout
from .layouts.grid import Grid
from .viewport import Viewport

logger = logging.getLogger(__name__)


class Window:
    """A GUI window and OpenGL context."""

    # The fallback height of the window in pixels when no valid settings value is available.
    DEFAULT_HEIGHT = 1000

    # The fallback width of the window in pixels when no valid settings value is available.
    DEFAULT_WIDTH = 1000

    def __init__(self, title: str, **kwargs):
        self._window_hints()

        width, height = self._window_size(kwargs.get("width"), kwargs.get("height"))
        self.glfw_window = self._create_window(title, width, height)

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

        if event.cursor_delta:
            event.cursor_delta.y = -event.cursor_delta.y

        if event.event_type is InputEventType.RESIZE:
            # Invalidate the cached window size now that the window has changed.
            if self.size:
                del self.size
            # Inform the layout that the window has changed so that viewports can also be scaled.
            self.layout.resize(event.size)
        else:
            self.layout.event(event)

    def _create_window(self, title: str, width: int, height: int) -> None:
        """Create the window with the provided settings using GLFW."""
        window = glfw.create_window(width, height, title, None, None)

        if not window:
            glfw.terminate()
            raise WindowError(glfw_detail_error("GLFW create window failed"))

        self._try_set_position(window)

        glfw.make_context_current(window)
        glfw.swap_interval(0)

        return window

    def _try_set_position(self, glfw_window) -> None:
        """Try to set the position of the window from the settings.

        The settings usually hold the position from the previous session. If this position is off
        the screen, they are ignored.
        """
        if "position" not in settings.window:
            return

        # Get the size of the current monitor.
        video_mode = glfw.get_video_mode(glfw.get_primary_monitor())

        # Ensure that the top left corner of the window is actually going to be placed on the
        # screen. Otherwise it may not be obvious to the user that the window even opened at all.
        for position, maximum in zip(settings.window.position, video_mode.size):
            if position < 0 or position > maximum:
                logger.debug("Using default window. Saved position would place window off screen")
                return

        glfw.set_window_pos(glfw_window, *settings.window.position)

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

    def _window_size(
        self, passed_width: Optional[int], passed_height: Optional[int]
    ) -> Tuple[int, int]:
        """Return the proposed window height and width.

        This method will try to provide valid values from the following sources in order:
            - Size passed to the Window constructor in `height` and `width` keyword arguments
            - Size saved in the `window` settings key under `height` and `width` keys.
            - Default size hard-coded into the `Window` class (`Window.DEFAULT_...`)

        A `WindowError` is raised if the size passed to the Window constructor is invalid.
        """
        # Always try to use what was provided to the constructor, unless it's not possible.
        dimensions = {"width": passed_width, "height": passed_height}

        for name, value in dimensions.items():
            if value is not None and value <= 0:
                raise WindowError(f"Provided window {name} must be positive. Got {value}")

            # When no value is provided, try to uses the settings value. Otherwise use the defaults.
            if value is None:
                # Ensure the settings value is valid before using it.
                settings_value = getattr(settings.window, name, 0)
                if settings_value > 0:
                    dimensions[name] = settings_value
                else:
                    logger.debug(
                        "Using a default window %s value as the setting is not found or invalid",
                        name,
                    )
                    dimensions[name] = getattr(Window, f"DEFAULT_{name.upper()}")

        return dimensions.values()

    def _window_hints(self) -> None:
        """Set window hints."""
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
        glfw.window_hint(glfw.RESIZABLE, True)
        glfw.window_hint(glfw.SAMPLES, 4)
