import abc
import math
from typing import Optional

from spatial3d import Matrix4


class Projection(abc.ABC):
    """A generic project base class."""

    def __init__(
        self,
        aspect: Optional[float] = None,
        near_clip: Optional[float] = None,
        far_clip: Optional[float] = None,
        **_kwargs
    ) -> None:
        # The width of the projection plane over the height of the projection plane.
        self.aspect = aspect or 1.0
        # The distance to the near clipping plane.
        self.near_clip = near_clip or 0.1
        # The distance to the far clipping plane.
        self.far_clip = far_clip or 10000

    @property
    def depth(self) -> float:
        """Return the distance between the near and far clipping planes."""
        return self.far_clip - self.near_clip

    @property
    @abc.abstractmethod
    def matrix(self) -> Matrix4:
        """Return the projection's matrix."""

    @property
    @abc.abstractmethod
    def inverse(self) -> Matrix4:
        """Return the projection's matrix inverse."""

    @abc.abstractmethod
    def resize(self, width: float, height: float) -> None:
        """Update the projection attributes for the provided width and height of the projection."""


class OrthoProjection(Projection):
    """An orthographic projection that consists of six clipping planes."""

    # The minimum allowable width (used to prevent excessive zooming in).
    WIDTH_MIN = 0.01

    def __init__(self, *, width: float = 1.0, **kwargs) -> None:
        super().__init__(**kwargs)
        # The distance between the left and right clipping planes.
        self.width = width

    @property
    def height(self) -> float:
        """Return the distance between the top and bottom clipping planes."""
        # Since the aspect ratio is defined, compute height instead of storing it.
        return self.width / self.aspect

    @height.setter
    def height(self, height: float):
        """Set the distance between the top and bottom clipping planes."""
        self.width = height * self.aspect

    @property
    def inverse(self) -> Matrix4:
        """Return the orthographic projection's matrix inverse."""
        m11 = self.width / 2
        m22 = self.height / 2
        m33 = -self.depth / 2
        m43 = -(self.far_clip + self.near_clip) / 2

        return Matrix4(
            [m11, 0.0, 0.0, 0.0, 0.0, m22, 0.0, 0.0, 0.0, 0.0, m33, m43, 0.0, 0.0, 0.0, 1.0]
        )

    @property
    def matrix(self) -> Matrix4:
        """Return the orthographic projection's matrix."""
        m11 = 2 / self.width
        m22 = 2 / self.height
        m33 = -2 / self.depth
        m34 = -(self.far_clip + self.near_clip) / self.depth

        return Matrix4(
            [m11, 0.0, 0.0, 0.0, 0.0, m22, 0.0, 0.0, 0.0, 0.0, m33, 0.0, 0.0, 0.0, m34, 1.0]
        )

    def resize(self, width: float, height: float) -> None:
        """Update the projection attributes for the provided width and height of the projection."""
        new_aspect = width / height
        # Scale the width by the ratio of new to old so that the scene does not change size when
        # the window changes size.
        self.width *= new_aspect / self.aspect
        self.aspect = new_aspect

    def zoom(self, amount: float) -> None:
        """Increase or decrease the level of zoom by the provided amount."""
        self.width = max(self.width + amount, OrthoProjection.WIDTH_MIN)


class PerspectiveProjection(Projection):
    """A perspective projection defined by vertical field of view."""

    def __init__(self, *, vertical_fov: float, **kwargs) -> None:
        super().__init__(**kwargs)

        # The vertical angle of viewing frustum.
        self.vertical_fov = vertical_fov

    @property
    def inverse(self) -> Matrix4:
        """Return the perspective projection's matrix inverse."""
        m11 = self.aspect / self._scale
        m22 = 1 / self._scale
        m43 = -self.depth / -(self.far_clip + self.near_clip)
        m44 = (self.far_clip + self.near_clip) / (2 * self.far_clip + self.near_clip)

        return Matrix4(
            [m11, 0.0, 0.0, 0.0, 0.0, m22, 0.0, 0.0, 0.0, 0.0, 0.0, m43, 0.0, 0.0, -1.0, m44]
        )

    @property
    def matrix(self) -> Matrix4:
        """Return the perspective projection's matrix inverse."""
        m11 = self._scale / self.aspect
        m22 = self._scale
        m33 = -(self.far_clip + self.near_clip) / self.depth
        m34 = -2 * self.far_clip * self.near_clip / self.depth

        return Matrix4(
            [m11, 0.0, 0.0, 0.0, 0.0, m22, 0.0, 0.0, 0.0, 0.0, m33, -1.0, 0.0, 0.0, m34, 0.0]
        )

    @property
    def horizontal_fov(self):
        """Return the horizontal angle of the viewing frustum."""
        return 2 * math.atan(self.aspect * math.tan(self.vertical_fov / 2))

    def resize(self, width: float, height: float) -> None:
        """Update the projection attributes for the provided width and height of the projection."""
        self.aspect = width / height

    @property
    def _scale(self):
        """Return the perspective scale factor."""
        return 1.0 / math.tan(self.vertical_fov / 2.0)
