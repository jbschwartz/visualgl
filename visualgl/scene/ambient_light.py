import dataclasses

from spatial3d import Vector3


@dataclasses.dataclass
class AmbientLight:
    """An ambient light."""

    position: Vector3
    color: Vector3
    intensity: float
