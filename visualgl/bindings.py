import dataclasses
import enum
import logging
from typing import Dict, List, Optional, Tuple

import glfw

from visualgl.window.input_event import InputEvent, InputEventType

from .exceptions import SettingsError

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class CommandRoute:
    """The route which a command binding will take on execution.

    That is, which controller and its method should handle the binding with the given parameter
    when it occurs. Parameters are optional. For example, `CommandRoute("camera", "orbit", "up")`
    represents the `CameraController.orbit` function call.
    """

    controller: str
    method: str
    parameter: Optional[str] = None


BindingsType = Dict[Tuple[int, int], CommandRoute]


@enum.unique
class _ScrollType(enum.IntEnum):
    """Integer constants for scroll input.

    GLFW does not provide integer constants for scrolling (since it is more of an action than a
    physical button or key). This enum is provided so that scrolling can be included in command
    bindings (e.g., settings.bindings = {"camera.scale": "z, scroll_vertical"})
    """

    # Use glfw.KEY_LAST to ensure there are no collisions between these constants and the ones used
    # by GLFW.
    VERTICAL = glfw.KEY_LAST + 1
    HORIZONTAL = glfw.KEY_LAST + 2


# pylint: disable=too-few-public-methods
class Bindings:
    """A collection of keyboard and mouse bindings that map user input onto commands.

    This class accepts key and mouse bindings as strings (usually from settings) into GLFW constants
    that can be matched against `InputEvents`.
    """

    def __init__(self, bindings: Dict[str, str]):
        self._bindings: BindingsType = self._translate_bindings(bindings)

    def command(self, event: InputEvent) -> Optional[CommandRoute]:
        """Return the matching command route for the given input event. Return None for no match."""
        # Input can come in the form of a key press, mouse button press, or scroll.
        if event.event_type is InputEventType.SCROLL:
            _input = int(_ScrollType.HORIZONTAL if event.scroll.x != 0 else _ScrollType.VERTICAL)
        else:
            _input = event.button if event.button is not None else event.key

        if _input is None:
            return None

        return self._bindings.get((event.modifiers, _input))

    def _get_glfw_constants(self, input_group: str) -> Tuple[int, int]:
        """Translate the settings string into the appropriate GLFW constants.

        For example, 'button_middle' becomes `glfw.MOUSE_BUTTON_MIDDLE` and 'control' becomes
        `glfw.MOD_CONTROL`.
        """
        # There can be several modifiers but only one input key or mouse button.
        *modifier_strings, input_string = input_group.upper().replace(" ", "").split("+")

        return (self._parse_modifiers(modifier_strings), self._parse_input(input_string))

    def _parse_input(self, string: str) -> int:
        """Parse the input string and return the corresponding GLFW constant."""
        assert (
            string.isdigit() or string.isupper()
        ), f"The input string '{string}' must already be uppercase."

        # GLFW prefixes all constants with "KEY" or "MOUSE".
        for prefix in ["KEY", "MOUSE"]:
            attribute_name = prefix + "_" + string
            if hasattr(glfw, attribute_name):
                return getattr(glfw, attribute_name)

        if string.startswith("SCROLL_"):
            try:
                return int(_ScrollType[string.replace("SCROLL_", "")])
            except KeyError:
                # Allow the exception at the end to catchall unknown inputs.
                pass

        raise SettingsError(f"Unknown input '{string.lower()}'")

    def _parse_modifiers(self, strings: List[str]) -> int:
        """Parse the input strings for modifiers and return the integer bit field."""
        bit_field = 0

        # Process modifiers one by one, ORing their integer value onto the running total.
        for modifier in strings:
            assert modifier.isupper(), f"The modifier string '{modifier}' must already be uppercase"

            # Allow settings to use "ctrl" as an abbreviation for "control".
            if modifier == "CTRL":
                modifier = "CONTROL"

            try:
                integer = getattr(glfw, f"MOD_{modifier}")
            except AttributeError as e:
                raise SettingsError(f"Unknown modifier key '{modifier.lower()}'") from e

            bit_field |= integer

        return bit_field

    def _translate_bindings(self, bindings: Dict[str, str]) -> BindingsType:
        """Return a dictionary of bindings from the string settings dictionary."""
        dictionary = {}

        # The settings dictionary contains string-string dictionary elements. The key represents the
        # command to be called. The value is a comma separated list of key and mouse presses
        # ("input groups") which are to be bound to the command.
        #
        # For example:
        #     {"camera.fit": "f,shift+b"}
        # Binds both the "f" key and "shift" and "b" keys to the "camera.fit" command.

        for command, input_groups in bindings.items():
            route = CommandRoute(*command.lower().split("."))
            for input_group in input_groups.split(","):
                try:
                    dictionary_key = self._get_glfw_constants(input_group)
                except SettingsError as e:
                    logger.warning("Ignoring binding for '%s': %s", command, str(e))
                    continue

                # Issue a warning if the dictionary entry is about to be overwritten.
                if dictionary_key in dictionary:
                    logger.warning(
                        "'%s' assigned to two commands: '%s' and '%s'. Assigning '%s' to '%s'",
                        input_group,
                        dictionary[dictionary_key],
                        command,
                        input_group,
                        command,
                    )

                dictionary[dictionary_key] = route

                logger.debug("Binding '%s' to '%s'", dictionary_key, command)

        return dictionary
