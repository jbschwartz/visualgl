from test.common import approx_v3
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture
from spatial3d import Vector3

from visualgl.window import Viewport


@pytest.fixture(name="concrete_viewport")
def fixture_concrete_viewport(mocker: MockerFixture) -> Mock:
    """Return a mock Viewport class."""
    mocker.patch.multiple(Viewport, __abstractmethods__=set())
    # pylint: disable=abstract-class-instantiated
    return Viewport


@pytest.mark.parametrize(
    "x_pos, y_pos, expected",
    [
        (100, 100, True),
        (100, 199, True),
        (199, 100, True),
        (199, 199, True),
        (150, 150, True),
        (200, 200, False),
        (298, 298, False),
    ],
)
def test_viewport_contains(
    concrete_viewport: Viewport, x_pos: int, y_pos: int, expected: Vector3
) -> None:
    """Test that given position is correctly identified as inside or outside of the Viewport."""
    viewport = concrete_viewport(Vector3(100, 100), Vector3(100, 100))

    assert (Vector3(x_pos, y_pos) in viewport) == expected


@pytest.mark.parametrize(
    "x_pos, y_pos, expected",
    [
        (100, 100, Vector3(-1, -1)),
        (100, 199, Vector3(-1, 1)),
        (199, 100, Vector3(1, -1)),
        (199, 199, Vector3(1, 1)),
        (150, 150, Vector3(1 / 99, 1 / 99)),
        (298, 298, Vector3(3, 3)),
    ],
)
def test_viewport_computes_ndc(
    concrete_viewport: Viewport, x_pos: int, y_pos: int, expected: Vector3
) -> None:
    """Test that the correct Normalized Device Coordinates are computed for a given position."""
    viewport = concrete_viewport(Vector3(100, 100), Vector3(100, 100))

    assert approx_v3(viewport.ndc(Vector3(x_pos, y_pos))) == expected
