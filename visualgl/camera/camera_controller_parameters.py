import enum
import math
from functools import cached_property

from spatial3d import Vector3, vector3


@enum.unique
class CameraView(enum.Enum):
    """Preset camera views that are defined by the view direction vector."""

    BACK = -Vector3.Y()
    BOTTOM = Vector3.Z()
    FRONT = Vector3.Y()
    ISOMETRIC = Vector3(-1, 1, -1)
    LEFT = Vector3.X()
    RIGHT = -Vector3.X()
    TOP = -Vector3.Z()

    @cached_property
    def up_vector(self) -> Vector3:
        """Return the up vector for the view.

        The up vector is assumed to the be the Z vector unless the view direction is colinear with
        Z. If the view direction is Z (respectively, -Z), then up is Y (respectively, -Y).
        """
        angle = vector3.angle_between(self.value, Vector3.Z())

        if math.isclose(angle, 0):
            return Vector3.Y()

        if math.isclose(angle, math.pi):
            return -Vector3.Y()

        return Vector3.Z()


@enum.unique
class OrbitDirection(enum.Enum):
    """Camera orbit directions."""

    DOWN = Vector3.Y()
    LEFT = -Vector3.X()
    RIGHT = Vector3.X()
    UP = -Vector3.Y()


@enum.unique
class RollDirection(enum.Enum):
    """Camera roll directions."""

    CLOCKWISE = -1
    COUNTER_CLOCKWISE = 1


@enum.unique
class ScaleDirection(enum.Enum):
    """Camera scale directions."""

    IN = -1
    OUT = 1


@enum.unique
class TrackDirection(enum.Enum):
    """Camera tracking directions."""

    DOWN = -Vector3.Y()
    LEFT = -Vector3.X()
    RIGHT = Vector3.X()
    UP = Vector3.Y()
