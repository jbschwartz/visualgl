import math
from typing import Dict

from spatial3d import Vector3


# Use the `pytest` convention for `approx` instead of PascalCase.
# pylint: disable=invalid-name
class approx_v3:
    """Approximate comparisons for `spatial3d.Vector3`.

    Akin to `pytest.approx`.
    """

    def __init__(self, vector: Vector3, rel_tol: float = None, abs_tol: float = None):
        self.vector = vector
        self.tolerances: Dict[str, float] = {}

        if rel_tol is not None:
            self.tolerances["rel_tol"] = rel_tol

        if abs_tol is not None:
            self.tolerances["abs_tol"] = abs_tol

    def __eq__(self, other) -> bool:
        """Return True if this vector and the other vector are approximately equal."""
        return (
            math.isclose(self.vector.x, other.x, **self.tolerances)
            and math.isclose(self.vector.y, other.y, **self.tolerances)
            and math.isclose(self.vector.z, other.z, **self.tolerances)
        )

    def __repr__(self) -> str:
        """Return a string with the vector for error reporting."""
        return repr(self.vector)
