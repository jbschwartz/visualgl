import abc
from typing import Iterator, List

from spatial3d import Vector3

from .input_event import InputEvent, InputEventType
from .viewport import Viewport


class Layout(abc.ABC):
    """A collection of viewports."""

    def __init__(self, viewports: List[Viewport]):
        self._viewports = viewports

    def __iter__(self) -> Iterator[Viewport]:
        """Return an iterator to the viewports in the layout."""
        return iter(self._viewports)

    @property
    def viewports(self) -> List[Viewport]:
        """Return a list of viewports in the layout."""
        return self._viewports

    @abc.abstractmethod
    def on_event(self, event: InputEvent) -> None:
        """Respond to the provided input event.

        Called by the window when raw mouse and keyboard events are captured.
        """

    @abc.abstractmethod
    def resize(self, size: Vector3) -> None:
        """Resize the layout to the provided `width` and `height` in pixels.

        This method is also responsible for resizing all child viewports.
        """

    def event(self, event: InputEvent) -> None:
        """Respond to the provided input event.

        Child classes of Layout should not override this function. Instead they should implement
        the `on_event` function which is called here.
        """
        if event.event_type is InputEventType.RESIZE:
            self.resize(event.size)

        self.on_event(event)
