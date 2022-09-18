import abc
from typing import Optional

import OpenGL.GL as gl
from spatial3d import Vector3

from .input_event import InputEvent


class Viewport(abc.ABC):
    """A generic section of a Window's output region.

    This class should be overridden with specific implementations which are responsible for dealing
    with the content and display of the viewport.
    """

    def __init__(self):
        # The location in pixels of the bottom-left corner of the viewport with respect to the
        # bottom-left corner of the full window.
        self.position: Optional[Vector3] = None

        # The width (`self.size.x`) and height (`self.size.y`) of the viewport in pixels.
        self.size: Optional[Vector3] = None

    def __enter__(self) -> "Viewport":
        """Activate the viewport for rendering."""
        assert (
            self.size is not None and self.position is not None
        ), "A viewport cannot be rendered before it is initialized"

        gl.glViewport(*self.position.xy, *self.size.xy)

        return self

    def __exit__(self, *args):
        """Deactivate the viewport for rendering."""

    @abc.abstractmethod
    def on_event(self, event: InputEvent) -> None:
        """Respond to the provided input event.

        Called by the layout when raw mouse and keyboard events are captured on the window.
        """

    @abc.abstractmethod
    def on_reflow(self, position: Vector3, size: Vector3) -> None:
        """Process the reflow of the viewport."""

    def event(self, event: InputEvent) -> None:
        """Respond to the provided input event.

        Child classes of Viewport should not override this function. Instead they should implement
        the `on_event` function which is called here.
        """
        if event.cursor_position:
            cursor_ndc = self.ndc(event.cursor_position)
            if event.cursor_delta:
                previous_cursor_ndc = self.ndc(event.cursor_position - event.cursor_delta)
                event.cursor_delta = cursor_ndc - previous_cursor_ndc

            event.cursor_position = cursor_ndc

        self.on_event(event)

    def reflow(self, position: Vector3, size: Vector3) -> None:
        """Update the position and size of the viewport.

        Child classes of Viewport should not override this function. Instead they should implement
        the `on_reflow` function which is called here.
        """
        assert position.x >= 0 and position.y >= 0 and size.x > 0 and size.y > 0, (
            f"The viewport must have positive, non-zero size and position. "
            f"Got size = {size.xy},  position = {position.xy}"
        )

        self.position = position
        self.size = size

        # Allow the child class to do any additional processing necessary.
        self.on_reflow(position, size)

    def ndc(self, cursor_position: Vector3) -> Vector3:
        """Return the normalized device coordinates at the provided cursor position (in pixels).

        Normalize device coordinates are a resolution-independent coordinate system. The bottom left
        corner is (-1, -1). The top right corner is (1, 1). The center of the viewport is (0, 0).

        The third component of the returned vector is always set to 0.
        """
        viewport_position = cursor_position - self.position + round(self.size, 0)
        return Vector3(
            2 * viewport_position.x / self.size.x - 1, 1 - 2 * viewport_position.y / self.size.y
        )
