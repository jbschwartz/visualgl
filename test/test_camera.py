import math
from test.common import approx_v3

import pytest
from spatial3d import CoordinateAxes, Vector3

from visualgl.camera import Camera, OrthoProjection


@pytest.fixture
def camera():
    return Camera()


def test_camera_initializes_with_default_transform(camera):
    assert getattr(camera, "position", None) is not None
    assert approx_v3(camera.position) == Vector3()

    assert getattr(camera, "camera_to_world", None) is not None
    assert getattr(camera, "world_to_camera", None) is not None

    basis = camera.camera_to_world.basis
    assert approx_v3(basis[CoordinateAxes.X]) == Vector3.X()
    assert approx_v3(basis[CoordinateAxes.Y]) == Vector3.Y()
    assert approx_v3(basis[CoordinateAxes.Z]) == Vector3.Z()

    assert getattr(camera, "projection", None) is not None
    assert isinstance(camera.projection, OrthoProjection)


def test_camera_orbit_does_not_change_distance_to_target(camera):
    target = Vector3(4, 5, 6)
    initial_position = camera.position

    initial_distance = (target - initial_position).length()

    camera.orbit(target, 1, 2)

    final_position = camera.position
    final_distance = (target - final_position).length()

    assert pytest.approx(initial_distance) == final_distance


def test_camera_roll_does_not_change_camera_position(camera):
    initial_position = camera.position
    camera.roll(math.radians(10))
    camera.roll(-math.radians(35))

    assert approx_v3(initial_position) == camera.position


def test_camera_track_moves_in_camera_space_x_and_y(camera):
    initial_position = camera.position
    initial_z_axis = camera.camera_to_world(Vector3.Z(), as_type="vector")

    track_amount_camera_space = Vector3(10, -10)
    track_amount_world_space = camera.camera_to_world(track_amount_camera_space, as_type="vector")

    camera.track(track_amount_camera_space.x, track_amount_camera_space.y)

    final_position = camera.position
    final_z_axis = camera.camera_to_world(Vector3.Z(), as_type="vector")

    # Check that the motion is orthogonal to the camera's Z axis
    delta = final_position - initial_position
    dot = delta * initial_z_axis

    assert pytest.approx(dot) == 0

    assert approx_v3(initial_position + track_amount_world_space) == camera.position
    assert approx_v3(initial_z_axis) == final_z_axis
