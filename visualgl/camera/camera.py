import enum
import math
from typing import Optional

from spatial3d import AABB, Quaternion, Ray, Transform, Vector3

from .exceptions import CameraError
from .projection import OrthoProjection, PerspectiveProjection, Projection


class OrbitType(enum.Enum):
    """Camera orbit type."""

    FREE = enum.auto()
    CONSTRAINED = enum.auto()


class Camera:
    """Basic camera model with positioning and manipulation."""

    def __init__(
        self, camera_to_world: Optional[Transform] = None, projection: Optional[Projection] = None
    ) -> None:
        self.projection = projection or OrthoProjection()
        self.camera_to_world = camera_to_world or Transform()

    @property
    def position(self) -> Vector3:
        """Return the current camera position in world space."""
        return self.camera_to_world.translation

    @position.setter
    def position(self, position: Vector3) -> Vector3:
        """Set the position of the camera in world space without changing its orientation."""
        self.camera_to_world = Transform.from_orientation_translation(
            self.camera_to_world.rotation, position
        )

    @property
    def world_to_camera(self) -> Transform:
        """Return the world-to-camera transformation."""
        return self.camera_to_world.inverse()

    def camera_space(self, ndc: Vector3) -> Vector3:
        """Transform a point in NDC to camera space. Place all points on the near clipping plane."""
        # Partially unproject the position and normalize
        # Choose the -z direction (so the ray comes out of the camera)
        m11 = self.projection.inverse.elements[0]
        m22 = self.projection.inverse.elements[5]

        return Vector3(m11 * ndc.x, m22 * ndc.y, -self.projection.near_clip)

    def cast_ray(self, ndc: Vector3) -> Ray:
        """Return a ray from the camera's position through the provided NDC coordinates.

        The ray's origin and direction are given in world coordinates.
        """
        point_camera_space = self.camera_space(ndc)

        if isinstance(self.projection, PerspectiveProjection):
            origin = self.position

            direction = point_camera_space
            direction.z = -1
            direction.normalize()
        elif isinstance(self.projection, OrthoProjection):
            origin = self.camera_to_world(self.camera_space(ndc), as_type="point")

            direction = Vector3(0, 0, -1)

        return Ray(origin, self.camera_to_world(direction, as_type="vector"))

    def dolly(self, z: float) -> None:
        """Move the camera along its line of sight (Z axis)."""
        self.camera_to_world *= Transform.from_axis_angle_translation(translation=Vector3(0, 0, z))

    def fit(self, world_aabb: AABB) -> None:
        """Adjust the camera's position and projection to fit the provided world bounding box."""
        camera_direction = self.camera_to_world.z_axis

        distance = world_aabb.sphere_radius()
        if isinstance(self.projection, PerspectiveProjection):
            # Determine if the scene is limited by the vertical or horizontal field of view.
            limiting_fov = min(self.projection.vertical_fov, self.projection.horizontal_fov) / 2
            distance /= math.sin(limiting_fov)
        else:
            # Orthographic projections do not move the camera but instead adjust the projection.
            # Similarly determine if the scene is limited in the width or height.
            limiting_direction = "width" if self.projection.aspect < 1 else "height"
            setattr(self.projection, limiting_direction, 2 * world_aabb.sphere_radius())

            # Keep the camera sufficiently far away to avoid clipping.
            distance *= 2

        self.position = world_aabb.center + camera_direction * distance

    def look_at(
        self, position: Vector3, target: Vector3, up_direction: Optional[Vector3] = None
    ) -> None:
        """Move the camera to look at the provided target from the given position and orientation.

        The provided vectors should be given in world coordinates. If an up direction is not
        provided, the world's Z-axis is used.

        This function recomputes the camera-to-world transformation by building the quaternion
        representation of a coordinate frame (3 vectors and a position).
        """
        up_direction = up_direction or Vector3.Z()

        # Negated since the camera looks down the negative Z axis.
        forward = -(target - position).normalize()

        try:
            right = (up_direction % forward).normalize()
        except ZeroDivisionError as e:
            raise CameraError(
                "Provided up orientation is ambiguous; it is coincident with the camera's direction"
            ) from e

        upward = (forward % right).normalize()

        self.camera_to_world = Transform.from_orientation_translation(
            Quaternion.from_basis(right, upward, forward), position
        )

    def orbit(
        self,
        target: Vector3,
        pitch: float = 0,
        yaw: float = 0,
        orbit_type: OrbitType = OrbitType.FREE,
    ) -> None:
        """Orbit the camera around target point (with pitch and yaw)."""
        # Free rotation is done around the camera's y axis. Constrained rotation uses the world Z
        # axis regardless of the camera's orientation.
        if orbit_type is OrbitType.FREE:
            yaw_axis = self.camera_to_world(Vector3.Y(), as_type="vector")
        else:
            yaw_axis = Vector3.Z()

        # Orbit first moves target position to the origin so that the camera rotates about the
        # target point (first around the X axis, then around the Y/Z axis as explained above). Then
        # the target is moved back to position so that a translation is not introduced.
        self.camera_to_world = (
            Transform.from_axis_angle_translation(translation=target)
            * Transform.from_axis_angle_translation(yaw_axis, yaw)
            * Transform.from_axis_angle_translation(self.camera_to_world.x_axis, pitch)
            * Transform.from_axis_angle_translation(translation=-target)
            * self.camera_to_world
        )

    def roll(self, angle: float) -> None:
        """Roll the camera around it's optical axis by the provided angle.

        Positive angles roll the camera in a counter-clockwise direction.
        """
        self.camera_to_world *= Transform.from_axis_angle_translation(Vector3.Z(), angle)

    def track(self, x: float = 0, y: float = 0, vector: Vector3 = None) -> None:
        """Move the camera vertically and horizontally in camera space."""
        # Accept vector input if it is provided. Makes calls a bit cleaner if the caller is using a
        # vector already.
        vector = Vector3(*vector.xy) if vector else Vector3(x, y)

        self.camera_to_world *= Transform.from_axis_angle_translation(translation=vector)
