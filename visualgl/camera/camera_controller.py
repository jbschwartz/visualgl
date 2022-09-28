import math
from operator import itemgetter
from typing import Optional

from spatial3d import Ray, Vector3, vector3

from visualgl import controller
from visualgl.scene import Scene
from visualgl.settings import settings

from .camera import Camera, OrbitType
from .camera_controller_parameters import (
    CameraView,
    OrbitDirection,
    RollDirection,
    ScaleDirection,
    TrackDirection,
)
from .projection import OrthoProjection, PerspectiveProjection


class CameraController(controller.Controller):
    """A keyboard and mouse controller for a Camera."""

    def __init__(self, scene: Scene):
        # The scene which the camera is viewing.
        self.scene = scene

        # The camera under control.
        self.camera: Camera = Camera()
        # The current target of the camera under control. This is used as a reference point for
        # several camera functions (e.g., orbiting).
        self.target: Vector3 = Vector3()
        # The orbit type to use when orbiting.
        self.orbit_type: OrbitType = OrbitType.CONSTRAINED
        # True when the camera is in a locked orientation. Several functions are disabled when this
        # is True to maintain the camera orientation.
        self.is_locked: bool = False

    @controller.command
    def fit(self) -> None:
        """Adjust the camera such that the entire scene fits in the view of the camera."""
        self.camera.fit(self.scene.aabb)

    @controller.command
    def lock_toggle(self) -> None:
        """Toggle the orientation lock on the camera."""
        self.is_locked = not self.is_locked

    @controller.command
    def normal_to(self) -> None:
        """Set the camera to the nearest saved view (excluding `CameraView.ISOMETRIC`).

        If the camera is already on the nearest view, flip direction and show the alternate view.
        For example, if the camera is on the front view, flip to the back view.
        """
        forward = self.camera.camera_to_world(-Vector3.Z(), as_type="vector")

        # Sort the list of views by the angle between the view direction and current camera
        # direction.
        views = sorted(
            [
                (view, vector3.angle_between(view.value, forward))
                for view in CameraView
                if view is not CameraView.ISOMETRIC
            ],
            key=itemgetter(1),
        )

        nearest, angle_between = views[0]

        # If the camera is already at the nearest view, flip the direction.
        if math.isclose(angle_between, 0):
            nearest, _ = views[-1]

        self.view(nearest)

    @controller.command
    def orbit(
        self,
        cursor_delta: Optional[Vector3],
        scroll: Optional[Vector3],
        direction: Optional[OrbitDirection] = None,
    ) -> None:
        """Orbit the camera in the provided direction or so that the scene follows the cursor.

        This function is ignored if the camera orientation is locked.
        """
        if self.is_locked:
            return

        if direction is not None:
            angles = settings.camera.orbit_step * direction.value
        elif scroll is not None:
            angles = settings.camera.orbit_step * scroll
        elif cursor_delta is not None:
            cursor_delta.x = -cursor_delta.x
            angles = settings.camera.orbit_speed * cursor_delta
        else:
            assert False, "No non-None arguments provided to orbit"

        yaw, pitch = angles.xy
        self.camera.orbit(self.target, pitch, yaw, self.orbit_type)

    @controller.command
    def orbit_toggle(self) -> None:
        """Toggle the orbit type used by the camera."""
        self.orbit_type = (
            OrbitType.FREE if self.orbit_type is OrbitType.CONSTRAINED else OrbitType.CONSTRAINED
        )

    @controller.command
    def projection_toggle(self):
        """Toggle the camera projection while maintaining the scale of the scene.

        That is, try to make scene's center point have the same Z NDC in both projections.
        """
        params = {
            "aspect": self.camera.projection.aspect,
            "near_clip": self.camera.projection.near_clip,
            "far_clip": self.camera.projection.far_clip,
            "vertical_fov": settings.camera.vertical_fov,
        }

        # The goal is to compute the width of the perspective frustum at the scene's center.
        point = self.camera.world_to_camera(self.scene.aabb.center, as_type="point")

        # Note that the width of the slice of the frustum is the aspect ratio times the height.
        # Then, the height is the tangent of half the vertical field of view times the distance
        # from the camera to the point.
        constant = -2 * params["aspect"] * math.tan(params["vertical_fov"] / 2)

        if isinstance(self.camera.projection, PerspectiveProjection):
            params["width"] = constant * point.z

            self.camera.projection = OrthoProjection(**params)

            # If the camera is inside the scene, conservatively move it outside (as otherwise there
            # is no way to as an orthogonal camera).
            # This can happen if the user brings the perspective camera inside the scene and then
            # switches to orthogonal.
            if self.scene.aabb.contains(self.camera.position):
                # This could cause clipping issues if the size of the scene is large
                # This could be circumvented by a more precise calculation of the distance to the
                # edge of the scene.
                self.camera.dolly(2 * self.scene.aabb.sphere_radius())
        else:
            # Calculate the change in camera Z position using the same logic as above.
            delta = point.z - (self.camera.projection.width / constant)
            self.camera.dolly(delta)

            self.camera.projection = PerspectiveProjection(**params)

    @controller.command
    def roll(
        self,
        cursor_position: Optional[Vector3],
        cursor_delta: Optional[Vector3],
        direction: Optional[RollDirection] = None,
    ) -> None:
        """Roll the camera in the provided direction or so that the scene follows the cursor.

        This function is ignored if the camera orientation is locked.
        """
        if self.is_locked:
            return

        if direction:
            angle = direction.value * settings.camera.roll_step
        else:
            # Calculate the radius vector from center screen to initial cursor position.
            radius = cursor_position - cursor_delta

            if math.isclose(radius.length(), 0):
                return

            # Calculate the unit tangent vector to the circle at the cursor start point.
            tangent = Vector3(radius.y, -radius.x).normalize()

            # The contribution to the roll is the projection of the cursor_delta vector onto the
            # tangent vector.
            angle = settings.camera.roll_speed * (cursor_delta * tangent)

        self.camera.roll(angle)

    @controller.command
    def scale(
        self,
        cursor_position: Optional[Vector3],
        cursor_delta: Optional[Vector3],
        scroll: Optional[Vector3],
        direction: Optional[ScaleDirection] = None,
    ) -> bool:
        """Attempt to scale the scene by the given amount. Return True if the scale is successful.

        Scaling is successful if it does not cause clipping in the scene.
        """
        if direction is not None:
            amount = direction.value * settings.camera.scale_step
        elif scroll is not None:
            self._scale_to_cursor(cursor_position, scroll.y * settings.camera.scale_in)
            return False
        elif cursor_delta is not None:
            amount = settings.camera.scale_speed * cursor_delta.y
        else:
            assert False, "No non-None arguments provided to `scale` method"

        if isinstance(self.camera.projection, PerspectiveProjection):
            if self._dolly_will_clip(amount):
                return False

            self.camera.dolly(amount)
        else:
            self.camera.projection.zoom(amount)

        return True

    @controller.command
    def track(
        self, cursor_delta: Optional[Vector3], direction: Optional[TrackDirection] = None
    ) -> None:
        """Track the camera in the provided direction or so the scene follows cursor movement."""
        if direction is not None:
            delta = -settings.camera.track_step * direction.value
        elif cursor_delta is not None:
            # assert not (math.isclose(cursor_delta.x, 0) or math.isclose(
            #     cursor_delta.y, 0)
            # ), "A cursor movement must be provided if no direction is provided ()."

            # Invert the delta so that the scene follows the cursor instead of the camera
            # following the cursor.
            delta = -self.camera.camera_space(cursor_delta)

            # This compensates for the distance from the camera to the item being hovered by the
            # mouse (and is only necessary for perspective projection). That is, the scene must be
            # translated further if the mouse has selected something farther in the distance and
            # vise versa.
            if isinstance(self.camera.projection, PerspectiveProjection):
                # Get the distance from the camera to the target.
                delta *= -self.camera.world_to_camera(self.target).z
        else:
            assert False, "No non-None arguments provided to `track` method"

        self.camera.track(vector=delta)

    @controller.command
    def view(self, view: CameraView) -> None:
        """Set the camera to the preset view.

        This function is ignored if the camera orientation is locked.
        """
        if self.is_locked:
            return

        # Move the camera outside of the scene bounding box using the viewing direction vector. The
        # `camera.fit` call at the end of the function makes this position somewhat arbitrary.
        camera_position = (
            self.scene.aabb.center - self.scene.aabb.sphere_radius() * view.value.normalize()
        )

        # Target the center of the scene.
        self.camera.look_at(camera_position, self.scene.aabb.center, view.up_vector)
        self.camera.fit(self.scene.aabb)

    def cast_ray(self, cursor_position: Vector3) -> Ray:
        """Return a ray in world coordinates from the camera position to the cursor."""
        return self.camera.cast_ray(cursor_position)

    def update_output_size(self, size: Vector3) -> None:
        """Update the output size of the camera."""
        assert size.x > 0 and size.y > 0, "Camera output size must be greater than zero."
        self.camera.projection.resize(*size.xy)

    def _dolly_will_clip(self, displacement: float) -> bool:
        """Return True if dollying the provided amount will clip the scene."""
        # Get the z value of the back of the scene in camera coordinates
        camera_box_points = self.camera.world_to_camera(self.scene.aabb.corners)
        back_of_scene = min(camera_box_points, key=lambda point: point.z)

        # If we're dollying out, don't allow the camera to exceed the clipping plane
        if displacement > 0 and (displacement - back_of_scene.z) > self.camera.projection.far_clip:
            return True

        return False

    def _scale_to_cursor(self, cursor_position: Vector3, direction: int) -> None:
        """Scale the camera in the direction of the cursor."""
        cursor_camera_point = self.camera.camera_space(cursor_position).normalize()

        # This is delta z for perspective and delta width for orthographic
        delta_scale = direction * settings.camera.scale_step
        delta_camera = cursor_camera_point * (delta_scale / cursor_camera_point.z)

        if isinstance(self.camera.projection, OrthoProjection):
            delta_camera /= self.camera.projection.width

        was_scaled = self.scale(None, Vector3(0, delta_scale), None, None)

        # Only follow the cursor when zooming in. When zooming out, go along the line of sight of
        # the camera.
        if was_scaled and delta_scale < 0:
            self.camera.track(delta_camera.x, delta_camera.y)
