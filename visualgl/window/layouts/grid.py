import itertools
import math
from typing import List, Tuple, Union

from spatial3d import Vector3

from ..exceptions import LayoutError
from ..input_event import InputEvent, InputEventType
from ..layout import Layout
from ..viewport import Viewport

GridSpec = Union[int, Tuple[float, ...]]


class Grid(Layout):
    """A uniform grid of viewports."""

    def __init__(self, viewports: List[Viewport], rows: GridSpec = 1, columns: GridSpec = 1):
        """Create a Grid layout.

        `rows` and `columns` are specified with either an integer (representing a number of equally
        sized cells) or with a tuple of floats where each float represents the width or height of
        the cell.

        If no `rows` or `columns` specifications are provided, the grid defaults to a single full
        sized cell (1 by 1).

        For example:
            `Grid(..., 2, 3)` creates a 2 rows by 3 columns grid of equally sized cells.

            `Grid(..., (0.6, 0.4), 3)` creates a 2 rows by 3 columns grid where the first row is
            60% of the overall height.

        Viewports should be provided in left-to-right, bottom-to-top. That is, the first viewport is
        the bottom left cell. The last viewport is the top right cell.
        """
        super().__init__(viewports)

        self.row_heights = self._parse_specification(rows)
        self.column_widths = self._parse_specification(columns)

        if len(self._viewports) != self.num_cells:
            raise LayoutError(
                f"Expected {self.num_cells} viewports but received {len(self._viewports)}"
            )

        # Make the focused viewport the top left corner.
        self.focused: Viewport = self._viewports[-len(self.row_heights)]

    @property
    def num_cells(self) -> int:
        """Return the number of cells in the grid."""
        return len(self.row_heights) * len(self.column_widths)

    def on_event(self, event: InputEvent) -> None:
        """Handle the input event."""
        # Identify which viewport was clicked on.
        if event.event_type is InputEventType.CLICK:
            for viewport in self._viewports:
                if event.cursor_position in viewport:
                    self.focused = viewport
                    break

        # Only pass events to the currently focused viewport (so mouse input does not move a camera
        # in a different viewport, for example).
        self.focused.event(event)

    def resize(self, size: Vector3) -> None:
        """Resize the overall grid to the provided `size` in pixels."""
        # Get the starting position for each cell by taking the partial sum of previous cells.
        row_positions = list(itertools.accumulate(self.row_heights, initial=0.0))
        column_positions = list(itertools.accumulate(self.column_widths, initial=0.0))

        cell_index = 0
        for row_height, row_position in zip(self.row_heights, row_positions):
            for column_width, column_position in zip(self.column_widths, column_positions):
                self._viewports[cell_index].reflow(
                    Vector3(int(column_position * size.x), int(row_position * size.y)),
                    Vector3(int(column_width * size.x), int(row_height * size.y)),
                )

                cell_index += 1

        assert cell_index == self.num_cells, (
            f"All {self.num_cells} viewport(s) should be updated by `resize`"
            f"(only updated {cell_index})"
        )

    def _parse_specification(self, specification: GridSpec) -> Tuple[float, ...]:
        # If an integer N is provided, create N equally sized cells.
        if isinstance(specification, int):
            if specification <= 0:
                raise LayoutError(
                    "An integer specification must be greater than or equal to 1."
                    f"Got {specification}"
                )
            specification = (1.0 / specification,) * specification
        else:
            total = sum(specification)
            if not math.isclose(total, 1.0):
                raise LayoutError(
                    f"The provided proportions {specification} do not sum to 1. Got {total}"
                )

            if any(math.isclose(size, 0) for size in specification):
                raise LayoutError(f"A cell cannot have zero width or height (in {specification})")

            if any(size < 0 for size in specification):
                raise LayoutError(
                    f"A cell cannot have negative width or height (in {specification})"
                )

        return specification
