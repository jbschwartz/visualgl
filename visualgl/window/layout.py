import abc
from typing import Iterator, List

from .viewport import Viewport


class Layout(abc.ABC):
    """A collection of viewports."""

    def __init__(self, viewports: List[Viewport]):
        self._viewports = viewports

    def __iter__(self) -> Iterator[Viewport]:
        return iter(self._viewports)

    @property
    def viewports(self) -> List[Viewport]:
        """Return a list of viewports in the layout."""
        return self._viewports

    @abc.abstractmethod
    def resize(self, width: int, height: int) -> None:
        """Resize the layout to the provided `width` and `height` in pixels.

        This method is also responsible for resizing all child viewports.
        """
