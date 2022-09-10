import enum
from typing import Optional

from spatial3d import AABB, CoordinateAxes, Quaternion, Ray, Transform, Vector3

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
        self.projection = projection or PerspectiveProjection()
        self.camera_to_world = camera_to_world or Transform()

    @property
    def position(self) -> Vector3:
        """Return the current camera position in world space."""
        return self.camera_to_world.translation

    def look_at(
        self, position: Vector3, target: Vector3, up_direction: Optional[Vector3] = None
    ) -> None:
        """Move the camera to look at the provided target from the given position and orientation.

        The provided vectors should be given in world coordinates. If an up direction is not
        provided, the world's Z-axis is used.

        This function recomputes the camera-to-world transformation by building the quaternion
        representation of a coordinate frame
        (3 vectors and a position).
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
        # Move target to the origin
        self.camera_to_world = (
            Transform.from_axis_angle_translation(translation=-target) * self.camera_to_world
        )

        if pitch != 0:
            # Rotation around camera x axis in world coordinates
            pitch_axis = self.camera_to_world(Vector3.X(), as_type="vector")
            self.camera_to_world = (
                Transform.from_axis_angle_translation(axis=pitch_axis, angle=pitch)
                * self.camera_to_world
            )
        if yaw != 0:
            if orbit_type is OrbitType.FREE:
                # Rotation around camera y axis in world coordinates
                yaw_axis = self.camera_to_world(Vector3.Y(), as_type="vector")
            elif orbit_type is OrbitType.CONSTRAINED:
                # Rotation around world z axis
                yaw_axis = Vector3.Z()

            self.camera_to_world = (
                Transform.from_axis_angle_translation(axis=yaw_axis, angle=yaw)
                * self.camera_to_world
            )

        # Move target back to position
        self.camera_to_world = (
            Transform.from_axis_angle_translation(translation=target) * self.camera_to_world
        )

    def dolly(self, z: float) -> None:
        """Move the camera along its line of sight (z axis)."""
        self.camera_to_world *= Transform.from_axis_angle_translation(translation=Vector3(0, 0, z))

    def track(self, x: float = 0, y: float = 0, vector: Vector3 = None) -> None:
        """Move the camera vertically and horizontally in camera space."""
        # Accept vector input if it is provided. Makes calls a bit cleaner if the caller is using a
        # vector already.
        vector = Vector3(*vector.xy) if vector else Vector3(x, y)

        self.camera_to_world *= Transform.from_axis_angle_translation(translation=vector)

    def roll(self, angle: float) -> None:
        """Roll the camera around it's optical axis by the provided angle.

        Positive angles roll the camera in a counter-clockwise direction.
        """
        self.camera_to_world *= Transform.from_axis_angle_translation(axis=Vector3.Z(), angle=angle)

    def fit(self, world_aabb: AABB, scale: float = 1) -> None:
        """Dolly and track the camera to fit the provided bounding box in world space.

        Scale [0, 1] represents the percentage of the frame used (with 1 being full frame).

        This function is not perfect but performs well overall. There may be some edge cases out
        there lurking.
        """

        # Check to see if the camera is in the scene bounding box
        # This function generally doesn't behave well with the camera inside the box
        # This is a bit of a cop-out since there are probably ways to handle those edge cases
        #   but those are hard to think about... and this works.
        if world_aabb.contains(self.position):
            self.camera_to_world *= Transform.from_axis_angle_translation(
                translation=Vector3(0, 0, world_aabb.sphere_radius())
            )

        # Centering the camera on the world bounding box first helps removes issues caused by
        # a major point skipping to a different corner as a result of the camera's zoom in movement.
        self.track(vector=self.world_to_camera(world_aabb.center))

        # Convert world bounding box corners to camera space
        camera_box_points = self.world_to_camera(world_aabb.corners)

        # Generate NDCs for a point in coordinate (z = 0, y = 1, z = 2)
        def ndc_coordinate(point, coordinate):
            clip = self.projection.project(point)
            return clip[coordinate]

        sorted_points = {}
        sizes = {}
        for coord in [CoordinateAxes.X, CoordinateAxes.Y]:
            # Find the points that create the largest width or height in NDC space
            sorted_points[coord] = sorted(
                camera_box_points, key=lambda point: -ndc_coordinate(point, coord)
            )
            # Calculate the distance between the two extreme points vertically and horizontally
            sizes[coord] = ndc_coordinate(sorted_points[coord][0], coord) - ndc_coordinate(
                sorted_points[coord][-1], coord
            )

        # We now want to make the NDC coordinates of the two extreme point (in x or y) equal to
        # 1 and -1.
        # This will mean the bounding box is as big as we can make it on screen without clipping it.
        #
        # To do this, both points are shifted equally to center them on the screen. Then both points
        # are made to 1 and -1 by adjusting z (since NDC.x = x / z and NDC.y = y / z).
        #
        # For the case of y being the limiting direction (but it is analogous for x) we use a system
        # of equations. Two equations and two unknowns (delta_y, delta_z), taken from the
        # projection matrix:
        #   aspect * (y_1 + delta_y) / (z_1 + delta_z) = -1
        #   aspect * (y_2 + delta_y) / (z_2 + delta_z) =  1
        #
        # Note the coordinates (y and z) are given in camera space
        def solve_deltas(major, v1, v2, v3, v4, projection_factor):
            """
            Solve the deltas for all three axis.

            If `major` is CoordinateAxes.X, the fit occurs on the width of the bounding box.
            If `major` is CoordinateAxes.Y, the fit occurs on the height of the bounding box.
            `v1` and `v2` are the points along the major axis.
            `v3` and `v4` are the points along hte minor axis.
            """
            delta_major = (
                -projection_factor * v1[major] - v1.z - projection_factor * v2[major] + v2.z
            ) / (2 * projection_factor)
            delta_distance = projection_factor * delta_major + projection_factor * v2[major] - v2.z

            minor = CoordinateAxes.X if major == CoordinateAxes.Y else CoordinateAxes.Y

            delta_minor = (-v4.z * v3[minor] - v3.z * v4[minor]) / (v3.z + v4.z)

            return (delta_major, delta_minor, delta_distance)

        x_min = sorted_points[CoordinateAxes.X][-1]
        x_max = sorted_points[CoordinateAxes.X][0]
        y_min = sorted_points[CoordinateAxes.Y][-1]
        y_max = sorted_points[CoordinateAxes.Y][0]

        if sizes[CoordinateAxes.Y] > sizes[CoordinateAxes.X]:
            # Height is the constraint: Y is the major axis
            if isinstance(self.projection, PerspectiveProjection):
                projection_factor = self.projection.matrix.elements[5] / scale
                delta_y, delta_x, delta_z = solve_deltas(
                    CoordinateAxes.Y, y_max, y_min, x_max, x_min, projection_factor
                )
            elif isinstance(self.projection, OrthoProjection):
                delta_x = -(x_max.x + x_min.x) / 2
                delta_y = -(y_max.y + y_min.y) / 2
                delta_z = 0

                self.projection.height = (y_max.y - y_min.y) / scale
        else:
            # Width is the constraint: X is the major axis
            if isinstance(self.projection, PerspectiveProjection):
                projection_factor = self.projection.matrix.elements[0] / scale
                delta_x, delta_y, delta_z = solve_deltas(
                    CoordinateAxes.X, x_max, x_min, y_max, y_min, projection_factor
                )
            elif isinstance(self.projection, OrthoProjection):
                delta_x = -(x_max.x + x_min.x) / 2
                delta_y = -(y_max.y + y_min.y) / 2
                delta_z = 0

                self.projection.width = (x_max.x - x_min.x) / scale

        # Move the camera, remembering to adjust for the box being shifted off center
        self.camera_to_world *= Transform.from_axis_angle_translation(
            translation=Vector3(-delta_x, -delta_y, -delta_z)
        )

    def camera_space(self, ndc: Vector3) -> Vector3:
        """Transform a point in NDC to camera space. Place all points on the near clipping plane."""
        # TODO: Verify that this is working correctly (with a test?).

        # Partially unproject the position and normalize
        # Choose the -z direction (so the ray comes out of the camera)
        m11 = self.projection.inverse.elements[0]
        m22 = self.projection.inverse.elements[5]

        return Vector3(m11 * ndc.x, m22 * ndc.y, -self.projection.near_clip)

    def cast_ray(self, ndc: Vector3) -> Ray:
        """Cast a ray from the camera's position into world space through the provided NDC
        coordinates.

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

    @property
    def world_to_camera(self) -> Transform:
        """Return the world-to-camera transformation."""
        return self.camera_to_world.inverse()
