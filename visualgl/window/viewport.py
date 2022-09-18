import abc
from typing import Optional

import OpenGL.GL as gl
from spatial3d import Vector3



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
    def on_reflow(self, position: Vector3, size: Vector3) -> None:
        """Process the reflow of the viewport."""

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
