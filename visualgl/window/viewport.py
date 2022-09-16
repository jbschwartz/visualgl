import abc
from typing import Tuple

import OpenGL.GL as gl
from spatial3d import CoordinateAxes


class Viewport(abc.ABC):
    """A section of a Window's output region."""

    def __init__(
        self, x_position: int = None, y_position: int = None, width: int = None, height: int = None
    ):
        self.position: Tuple[int, int] = (x_position, y_position)
        self.size: Tuple[int, int] = (width, height)

    def __enter__(self) -> "Viewport":
        """Activate the viewport for rendering."""
        gl.glViewport(
            self.position[CoordinateAxes.X],
            self.position[CoordinateAxes.Y],
            self.size[CoordinateAxes.X],
            self.size[CoordinateAxes.Y],
        )

        return self

    def __exit__(self, *args):
        """Deactivate the viewport for rendering."""

    @abc.abstractmethod
    def on_reflow(self, position: Tuple[int, int], size: Tuple[int, int]) -> None:
        """Process the reflow of the viewport."""

    def reflow(self, position: Tuple[int, int], size: Tuple[int, int]) -> None:
        """Update the position and size of the viewport.

        Child classes of Viewport should not override this function. Instead they should implement
        the `on_reflow` function which is called here.
        """
        self.position = position
        self.size = size

        # Allow the child class to do any additional processing necessary.
        self.on_reflow(position, size)
