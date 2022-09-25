import math

from spatial3d import Transform, vector3

from ..settings import settings
from .camera import Camera, OrbitType
from .projection import OrthoProjection, PerspectiveProjection

Vector3 = vector3.Vector3


class CameraController:
    VIEWS = {
        "top": {"position": Vector3(0, 0, 1250), "up": Vector3(0, 1, 0)},
        "bottom": {"position": Vector3(0, 0, -1250), "up": Vector3(0, -1, 0)},
        "left": {"position": Vector3(-1250, 0, 500)},
        "right": {"position": Vector3(1250, 0, 500)},
        "front": {"position": Vector3(0, -1250, 500)},
        "back": {"position": Vector3(0, 1250, 500)},
        "iso": {"position": Vector3(750, -750, 1250)},
    }

    def __init__(self, scene):
        self.camera = Camera()
        self.scene = scene

        self.target = Vector3()
        self.orbit_type = OrbitType.CONSTRAINED

    def cast_ray(self, cursor_position):
        return self.camera.cast_ray(cursor_position)

    def command(self, event):
        _module, command, parameter, *_ = event.command + [None]

        if command == "track":
            self.track(event.cursor_delta, parameter)

        elif command == "roll":
            self.roll(event.cursor_position, event.cursor_delta, parameter)

        elif command == "scale":
            if getattr(event.scroll, "y", None) is not None:
                self.scale_to_cursor(
                    event.cursor_position, event.scroll.y * settings.camera.scale_in
                )
            else:
                self.scale(event.cursor_delta, parameter)

        elif command == "orbit":
            if getattr(event.scroll, "x", None) is not None:
                self.camera.orbit(
                    self.target, 0, settings.camera.orbit_step * event.scroll.x, self.orbit_type
                )
            else:
                self.orbit(event.cursor_delta, parameter)

        elif command == "fit":
            self.camera.fit(self.scene.aabb)

        elif command == "orbit_toggle":
            self.orbit_type = (
                OrbitType.FREE
                if self.orbit_type is OrbitType.CONSTRAINED
                else OrbitType.CONSTRAINED
            )
        elif command == "projection_toggle":
            self.toggle_projection()
        elif command == "normal_to":
            self.normal_to()

        elif command == "view":
            self.view(parameter)

    def update_output_size(self, size: Vector3) -> None:
        """Update the output size of the camera."""
        assert size.x > 0 and size.y > 0, "Camera output size must be greater than zero."
        self.camera.projection.resize(*size.xy)

    def orbit(self, cursor_delta, direction: str) -> None:
        if direction == "left":
            self.camera.orbit(self.target, 0, -settings.camera.orbit_step, self.orbit_type)
        elif direction == "right":
            self.camera.orbit(self.target, 0, settings.camera.orbit_step, self.orbit_type)
        elif direction == "up":
            self.camera.orbit(self.target, -settings.camera.orbit_step, 0, self.orbit_type)
        elif direction == "down":
            self.camera.orbit(self.target, settings.camera.orbit_step, 0, self.orbit_type)
        else:
            cursor_delta.x = -cursor_delta.x
            angle = settings.camera.orbit_speed * cursor_delta
            self.camera.orbit(self.target, angle.y, angle.x, self.orbit_type)

    def normal_to(self) -> None:
        minimum = math.radians(180)
        direction = Vector3()
        forward = self.camera.camera_to_world(Vector3.Z(), as_type="vector")
        for coordinate in [
            Vector3.X(),
            Vector3.Y(),
            Vector3.Z(),
            -Vector3.X(),
            -Vector3.Y(),
            -Vector3.Z(),
        ]:
            angle = vector3.angle_between(coordinate, forward)
            if angle < minimum:
                minimum = angle
                direction = coordinate

        axis = vector3.cross(forward, direction)
        self.camera.camera_to_world = (
            Transform.from_axis_angle_translation(axis=axis, angle=minimum)
            * self.camera.camera_to_world
        )

        right = self.camera.camera_to_world(Vector3.X(), as_type="vector")

        first_direction = direction
        minimum = math.radians(180)
        for coordinate in [Vector3.X(), Vector3.Y(), Vector3.Z()]:
            if first_direction == coordinate:
                continue

            angle = vector3.angle_between(coordinate, right)
            if angle < minimum:
                minimum = angle
                direction = coordinate

        axis = vector3.cross(right, direction)
        self.camera.camera_to_world = (
            Transform.from_axis_angle_translation(axis=axis, angle=minimum)
            * self.camera.camera_to_world
        )

    def toggle_projection(self):
        """
        Switch the camera projection while maintaining "scale".

        That is, we try to make ndc_perspective = ndc_orthographic at the scene's center point.
        We use the x coordinate and obtain: m11 * camera_x / - camera_z = 2 / width * camera_x
          With m11 being the first element in the perspective projection matrix.
        """
        params = {
            "aspect": self.camera.projection.aspect,
            "near_clip": self.camera.projection.near_clip,
            "far_clip": self.camera.projection.far_clip,
            "vertical_fov": settings.camera.vertical_fov,
        }

        if isinstance(self.camera.projection, PerspectiveProjection):
            point = self.camera.world_to_camera(self.scene.aabb.center, as_type="point")
            # Calculate the width from the above relation
            params["width"] = -2 * point.z / self.camera.projection.matrix.elements[0]

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
            width = self.camera.projection.width

            self.camera.projection = PerspectiveProjection(**params)
            current = self.camera.world_to_camera(self.scene.aabb.center, as_type="point")

            # Calculate the z camera position from the above relation
            desired = -self.camera.projection.matrix.elements[0] * width / 2
            delta = current.z - desired

            if not self.dolly_will_clip(delta):
                self.camera.dolly(delta)

    def dolly_will_clip(self, displacement: float) -> bool:
        """Return True if dollying the provided amount will clip the scene."""
        # Get the z value of the back of the scene in camera coordinates
        camera_box_points = self.camera.world_to_camera(self.scene.aabb.corners)
        back_of_scene = min(camera_box_points, key=lambda point: point.z)

        # If we're dollying out, don't allow the camera to exceed the clipping plane
        if displacement > 0 and (displacement - back_of_scene.z) > self.camera.projection.far_clip:
            return True

        return False

    def track(self, cursor_delta: Vector3, direction: str) -> None:
        """Move the camera the same amount that the cursor moved.

        That is, calculate the distance in cursor distance in NDC and convert that to camera motion.
        """
        # Invert the delta in places so that the position of the scene follows the cursor
        # as opposed to the position of the camera following the cursor.
        if cursor_delta is None:
            if direction == "left":
                self.camera.track(-settings.camera.track_step, 0)
            elif direction == "right":
                self.camera.track(settings.camera.track_step, 0)
            elif direction == "up":
                self.camera.track(0, settings.camera.track_step)
            elif direction == "down":
                self.camera.track(0, -settings.camera.track_step)

            return

        delta = self.camera.camera_space(cursor_delta)

        if isinstance(self.camera.projection, PerspectiveProjection):
            delta *= -self.camera.world_to_camera(self.target).z

        self.camera.track(vector=-delta)

    def scale_to_cursor(self, cursor: Vector3, direction: int) -> None:
        cursor_camera_point = self.camera.camera_space(cursor)

        # This is delta z for perspective and delta width for orthographic
        delta_scale = direction * settings.camera.scale_step
        delta_camera = -cursor_camera_point * delta_scale

        if isinstance(self.camera.projection, OrthoProjection):
            delta_camera /= self.camera.projection.width

        was_scaled = self.scale(Vector3(0, delta_scale), None)

        if was_scaled:
            self.camera.track(delta_camera.x, delta_camera.y)

    def roll(self, cursor: Vector3, cursor_delta: Vector3, direction: str) -> float:
        if direction == "cw":
            self.camera.roll(-settings.camera.roll_step)
        elif direction == "ccw":
            self.camera.roll(settings.camera.roll_step)
        else:
            # Calculate the radius vector from center screen to initial cursor position.
            radius = cursor - cursor_delta

            if math.isclose(radius.length(), 0):
                return 0

            # Calculate the unit tangent vector to the circle at cursor_start_point.
            tangent = Vector3(radius.y, -radius.x).normalize()
            # The contribution to the roll is the projection of the cursor_delta vector onto the
            # tangent vector.
            angle = settings.camera.roll_speed * cursor_delta * tangent
            self.camera.roll(angle)

    def scale(self, cursor_delta, direction: str) -> bool:
        """Attempt to scale the scene by the given amount. Return True if the scale is successful.

        Scaling is successful if it does not cause clipping in the scene.
        """

        if direction == "in":
            amount = -settings.camera.scale_step
        elif direction == "out":
            amount = settings.camera.scale_step
        else:
            amount = settings.camera.scale_speed * cursor_delta.y

        if isinstance(self.camera.projection, PerspectiveProjection):
            if self.dolly_will_clip(amount):
                return False

            self.camera.dolly(amount)
        else:
            self.camera.projection.zoom(amount)

        return True

    def view(self, view_name: str) -> None:
        view = self.VIEWS[view_name]

        self.camera.look_at(
            view["position"], view.get("target", Vector3(0, 0, 500)), view.get("up", Vector3.Z())
        )
        self.camera.fit(self.scene.aabb)
