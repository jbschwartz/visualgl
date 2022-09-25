import logging
from typing import Callable, Optional, Tuple

import glfw

from visualgl.bindings import Bindings
from visualgl.utils import sign

from .exceptions import WindowError
from .input_event import InputEvent, InputEventType
from .window import Window

logger = logging.getLogger(__name__)


def _glfw_callback(function):
    """Decorate the method as a GLFW callback function."""
    # pylint: disable=protected-access
    # Use a protected attribute so as not to disturb any aspects of the function.
    function._glfw_callback = getattr(glfw, f"set_{function.__name__.lstrip('_')}_callback")
    return function


# pylint: disable=too-few-public-methods
class InputHandler:
    """A wrapper around GLFW for collecting raw mouse and keyboard events."""

    def __init__(
        self, window: Window, bindings: Bindings, event_callback: Optional[Callable] = None
    ):
        """Create an InputHandler to handle input events on the provided window.

        All events will be processed and passed to the provided `event_callback`.

        If no `event_callback` is given, try looking for an `event` method on the window. If one is
        not available, raise a `WindowError`.
        """
        if not event_callback:
            if not (event_callback := getattr(window, "event", None)):
                raise WindowError("No event callback found on window. Ignoring all input")

            logger.debug("Using the default window event callback")

        self._event_callback = event_callback

        # The keyboard and mouse bindings used to translate raw GLFW input into application actions.
        self.bindings = bindings

        # The current mouse button being held down in the window. Use None if no button is pressed.
        # Note: GLFW uses 0 to represent the left mouse button so do not attempt to clear this
        # value by setting to 0. Modifiers do not suffer from this problem.
        self.current_button_down: Optional[int] = None
        # Store the currently held down or released modifiers (e.g., shift). This attribute
        # functions like a bit field with each bit representing a different key.
        self.current_key_modifiers: int = 0

        # The last recorded cursor position in pixels.
        self.last_cursor_position: Optional[Tuple[int, int]] = None

        self._set_glfw_callbacks(window.glfw_window)

    def _emit(self, event: InputEvent) -> None:
        """Emit the provided event if a matching command is found."""
        # Ignore key and button release and repeat events.
        if event.event_type in [InputEventType.KEY, InputEventType.CLICK] and event.action in [
            glfw.RELEASE,
            glfw.REPEAT,
        ]:
            return

        if command := self.bindings.command(event):
            event.command = command

        self._event_callback(event)

    def _set_glfw_callbacks(self, glfw_window) -> None:
        """Set all decorated callback methods on this instance as GLFW callbacks.

        The GLFW callbacks process the raw mouse and keyboard events and pass an `InputEvent` object
        onto the event callback (`self.event_callback`) which is responsible for informing the rest
        of the library.
        """
        # Loop over all the attributes and methods on this instance and find those that have an
        # `_glfw_callback` attribute on them. This is set by the `@_glfw_callback` decorator.
        for name in filter(lambda name: not name.startswith("__"), dir(self)):
            glfw_callback = getattr(self, name)
            if callback_setter := getattr(glfw_callback, "_glfw_callback", None):
                # A callback wrapper is created by the factory so that the glfw callback function
                # is passed the event callback function.
                callback_setter(glfw_window, glfw_callback)

    @_glfw_callback
    def _cursor_pos(self, _glfw_window, x_position: int, y_position: int) -> None:
        """Emit the cursor position event or drag event if there are pressed mouse buttons.

        GLFW provides the X and Y position with respect to the top left corner of the window where
        X runs positive from left to right and Y runs positive from top to bottom.
        """
        cursor_position = (x_position, y_position)

        cursor_delta = (0, 0)
        if self.last_cursor_position is not None:
            cursor_delta = (
                cursor_position[0] - self.last_cursor_position[0],
                cursor_position[1] - self.last_cursor_position[1],
            )

        self._emit(
            InputEvent.Movement(
                self.current_button_down,
                cursor_position,
                cursor_delta,
                self.current_key_modifiers,
            )
        )

        self.last_cursor_position = cursor_position

    @_glfw_callback
    def _key(self, _glfw_window, key: int, _scancode, action: int, modifiers: int) -> None:
        """Emit the key event for key presses, releases, and repeats."""
        self.current_key_modifiers = modifiers
        self._emit(InputEvent.Key(key, action, self.current_key_modifiers))

    @_glfw_callback
    def _mouse_button(self, glfw_window, button: int, action: int, modifiers: int) -> None:
        """Emit the click event for clicks and releases."""
        self._emit(InputEvent.Click(button, action, glfw.get_cursor_pos(glfw_window), modifiers))

        # Record which mouse button is being held down. This does not support holding down multiple
        # buttons at once.
        self.current_button_down = button if action == glfw.PRESS else None

    @_glfw_callback
    def _scroll(self, glfw_window, x_direction: float, y_direction: float) -> None:
        """Emit the scroll event for both scroll directions."""
        assert x_direction != 0 or y_direction != 0, "Malformed scroll event encountered."

        # The scroll amounts are normalized by only passing on their direction.
        self._emit(
            InputEvent.Scroll(
                sign(x_direction),
                sign(y_direction),
                glfw.get_cursor_pos(glfw_window),
                self.current_key_modifiers,
            )
        )

    @_glfw_callback
    def _window_size(self, _window, width: int, height: int) -> None:
        """Emit the window resize event."""
        self._emit(InputEvent.Resize(width, height))
