from typing import Callable, List, Tuple, Union
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from visualgl.window import Grid, Viewport
from visualgl.window.exceptions import LayoutError


@pytest.fixture(name="grid")
def fixture_grid(mock_viewports: Callable) -> Callable[[int, int], Grid]:
    """Return a Grid factory which accepts a number of rows and columns."""

    def factory(rows: int, columns: int) -> Grid:
        return Grid(mock_viewports(rows * columns), rows, columns)

    return factory


@pytest.fixture(name="mock_viewport")
def fixture_mock_viewport(mocker: MockerFixture) -> Mock:
    """Return a mock Viewport class."""
    mock = mocker.Mock(spec=Viewport, side_effect=mocker.Mock)
    mock.reflow.return_value = None

    return mock


@pytest.fixture(name="mock_viewports")
def fixture_mock_viewports(mock_viewport: Mock) -> Callable[[int], List[Mock]]:
    """Return a mock Viewport factory which accepts a number a produces a list of viewports."""

    def factory(number: int) -> List[Mock]:
        return [mock_viewport() for _ in range(number)]

    return factory


def test_grid_defaults_to_a_single_cell(mock_viewports: Callable) -> None:
    """Test that the correct number of rows and columns are created."""
    grid = Grid(mock_viewports(1))

    assert len(grid.row_heights) == 1
    assert len(grid.column_widths) == 1
    assert grid.num_cells == 1


def test_grid_accepts_integers_for_rows_and_columns_arguments(mock_viewports: Callable) -> None:
    """Test that the correct number of rows and columns are created."""
    rows, columns = (2, 3)
    num_cells = rows * columns

    grid = Grid(mock_viewports(num_cells), rows, columns)

    assert len(grid.row_heights) == rows
    assert len(grid.column_widths) == columns


@pytest.mark.parametrize("rows, columns", [(-2, 2), (2, -2), (0, 2), (0, 2)])
def test_grid_raises_for_invalid_rows_and_columns_arguments(
    mock_viewports: Callable, rows: int, columns: int
) -> None:
    """Test that LayoutError is raised for invalid integer values (zero or negative)."""
    num_cells = rows * columns
    with pytest.raises(LayoutError):
        _ = Grid(mock_viewports(num_cells), rows, columns)


def test_grid_accepts_tuple_of_floats_of_cell_size_percentages(mock_viewports: Callable) -> None:
    """Test that the correct number of rows and columns are created from tuple of floats."""
    rows, columns = ((0.5, 0.5), (1 / 3, 1 / 3, 1 / 3))
    num_cells = len(rows) * len(columns)

    grid = Grid(mock_viewports(num_cells), rows, columns)

    assert grid.num_cells == num_cells


@pytest.mark.parametrize(
    "num_cells, rows, columns",
    [
        (4, 2, (0, 1)),
        (4, 2, (-0.5, 1.5)),
        (4, 2, (0.1, 0.1)),
        (4, (0, 1), 2),
        (4, (-0.5, 1.5), 2),
        (4, (0.1, 0.1), 2),
    ],
)
def test_grid_raises_for_invalid_tuple_of_floats(
    mock_viewports: Callable, num_cells: int, rows: Union[int, Tuple], columns: Union[int, Tuple]
) -> None:
    """Test that LayoutError is raised for tuples which do not sum to 1.0 or have invalid values.

    An invalid value is either zero or negative.
    """
    with pytest.raises(LayoutError):
        _ = Grid(mock_viewports(num_cells), rows, columns)


def test_grid_raises_for_incorrect_number_of_viewports() -> None:
    """Test that LayoutError is raised for invalid integer values (zero or negative)."""
    with pytest.raises(LayoutError):
        _ = Grid([], 2, 2)


def test_grid_num_cells_returns_the_number_of_cells(grid: Callable) -> None:
    """Test that the product of the number of rows and columns is returned."""
    rows, columns = (2, 3)
    num_cells = rows * columns

    test_grid = grid(rows, columns)

    assert test_grid.num_cells == num_cells


def test_grid_reflow_reflows_all_viewports(grid: Callable) -> None:
    """Test that the reflow function is called once on all viewports when the grid is reflowd.

    Test that the pixel sizes passed to the reflow function are correct and they are applied to the
    proper viewport order.
    """
    test_grid = grid(2, 2)
    test_grid.resize(100, 200)

    assert all(viewport.reflow.call_count == 1 for viewport in test_grid)

    assert test_grid.viewports[0].reflow.call_args.args == ((0, 0), (50, 100))
    assert test_grid.viewports[1].reflow.call_args.args == ((50, 0), (50, 100))
    assert test_grid.viewports[2].reflow.call_args.args == ((0, 100), (50, 100))
    assert test_grid.viewports[3].reflow.call_args.args == ((50, 100), (50, 100))
