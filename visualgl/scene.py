import abc

from spatial3d import AABB, Intersection, Ray, Vector3

from .ambient_light import AmbientLight


class Scene(abc.ABC):
    """A collection of objects and lights in a virtual scene."""

    def __init__(self, **kwargs) -> None:
        self.entities = []
        self.light = kwargs.get("light", AmbientLight(Vector3(0, -750, 350), Vector3(1, 1, 1), 0.3))

    @property
    def aabb(self) -> AABB:
        """Get the AABB for all simulation entities."""
        aabbs = [entity.aabb for entity in self.entities]

        return AABB(aabbs)

    @abc.abstractmethod
    def on_update(self, delta: float) -> None:
        """Called by the Viewport when the scene should be updated.

        `delta` represents the amount of time elapsed since the last update.
        """

    def intersect(self, ray: Ray) -> Intersection:
        """Intersect a ray with all scene entities and return closest found Intersection.

        Return Intersection.Miss() for no intersection.
        """
        if not self.aabb.intersect(ray):
            return Intersection.Miss()

        return ray.closest_intersection(self.entities)

    def update(self, delta: float) -> None:
        """Called by the Viewport when the scene should be updated.

        `delta` represents the amount of time elapsed since the last update.

        Child classes of Scene should not override this function. Instead they should implement
        the `on_update` function which is called here.
        """
        self.on_update(delta)
