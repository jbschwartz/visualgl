import enum
from typing import Optional, Tuple

from spatial3d import Vector3


class InputEventType(enum.Enum):
    """The type of InputEvent."""

    CLICK = enum.auto()
    CURSOR = enum.auto()
    DRAG = enum.auto()
    KEY = enum.auto()
    RESIZE = enum.auto()
    SCROLL = enum.auto()


# pylint: disable=too-few-public-methods,too-many-instance-attributes,invalid-name
class InputEvent:
    """A thin wrapper for GLFW input callback information.

    This class takes the disparate GLFW callback method arguments and makes a singular object that
    can be consumed by the rest of the library. See `InputHandler`.

    Further, it provides a layer of indirection to include more information than GLFW normally
    provides and to normalize/transform data types into something more library specific (e.g.,
    position is stored as a `Vector3`).
    """

    def __init__(self, event_type: InputEventType, **kwargs):
        self.event_type = event_type

        self.action: Optional[int] = kwargs.get("action")
        self.button: Optional[int] = kwargs.get("button")
        self.command: Optional[Tuple[str, str, Optional[str]]] = None
        self.cursor_delta: Optional[Vector3] = kwargs.get("cursor_delta")
        self.cursor_position: Optional[Vector3] = kwargs.get("cursor_position")
        self.key: Optional[int] = kwargs.get("key")
        self.modifiers: Optional[int] = kwargs.get("modifiers")
        self.scroll: Optional[Vector3] = kwargs.get("scroll")
        self.size: Optional[Vector3] = kwargs.get("size")

    @classmethod
    def Click(
        cls, button: int, action: int, cursor_position: Tuple[int, int], modifiers: int
    ) -> "InputEvent":
        """Create a Click type InputEvent."""
        return cls(
            InputEventType.CLICK,
            action=action,
            button=button,
            cursor_position=Vector3(*cursor_position),
            modifiers=modifiers,
        )

    @classmethod
    def Key(cls, key: int, action: int, modifiers: int) -> "InputEvent":
        """Create a Key type InputEvent."""
        return cls(InputEventType.KEY, action=action, key=key, modifiers=modifiers)

    @classmethod
    def Movement(
        cls,
        button: int,
        cursor_position: Tuple[int, int],
        cursor_delta: Tuple[int, int],
        modifiers: int,
    ) -> "InputEvent":
        """Create a Cursor or Drag type InputEvent."""
        event_type = InputEventType.DRAG if button is not None else InputEventType.CURSOR

        return cls(
            event_type,
            button=button,
            cursor_position=Vector3(*cursor_position),
            cursor_delta=Vector3(*cursor_delta),
            modifiers=modifiers,
        )

    @classmethod
    def Resize(cls, width: int, height: int) -> "InputEvent":
        """Create a Resize type InputEvent."""
        return cls(InputEventType.RESIZE, size=Vector3(width, height))

    @classmethod
    def Scroll(
        cls, x_direction: int, y_direction: int, cursor_position: Tuple[int, int], modifiers: int
    ) -> "InputEvent":
        """Create a Scroll type InputEvent."""
        return cls(
            InputEventType.SCROLL,
            cursor_position=Vector3(*cursor_position),
            scroll=Vector3(x_direction, y_direction),
            modifiers=modifiers,
        )
