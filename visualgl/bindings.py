import logging
from typing import Dict, Optional, Tuple

import glfw

from visualgl.window.input_event import InputEvent

from .exceptions import SettingsError

logger = logging.getLogger(__name__)

BindingsType = Dict[Tuple[int, int], str]


# pylint: disable=too-few-public-methods
class Bindings:
    """A collection of keyboard and mouse bindings that map user input onto commands.

    This class accepts key and mouse bindings as strings (usually from settings) into GLFW constants
    that can be matched against `InputEvents`.
    """

    def __init__(self, bindings: Dict[str, str]):
        self._bindings: BindingsType = self._translate_bindings(bindings)

    def command(self, event: InputEvent) -> Optional[str]:
        """Return the command that matches the given input event. Return None for no match."""
        if event.key is None:
            if event.button is None:
                return None

            key_or_button = event.button
        else:
            key_or_button = event.key

        return self._bindings.get((event.modifiers, key_or_button))

    def _get_glfw_constants(self, keys: str) -> Tuple[int, int]:
        """Translate the settings string into the appropriate GLFW constants.

        For example, 'button_middle' becomes `glfw.MOUSE_BUTTON_MIDDLE` and 'control' becomes
        `glfw.MOD_CONTROL`.
        """
        # There can be several modifiers but only one key or button.
        *modifier_strings, key_or_button_string = keys.upper().replace(" ", "").split("+")

        modifiers = 0
        # Process modifiers one by one, ORing their integer value onto the running total.
        if len(modifier_strings) > 0:
            for modifier in modifier_strings:
                # Allow settings to use "ctrl" as an abbreviation for "control".
                if modifier == "CTRL":
                    modifier = "CONTROL"

                try:
                    modifier = getattr(glfw, f"MOD_{modifier}")
                except AttributeError as e:
                    raise SettingsError(f"Unknown modifier key '{modifier.lower()}'") from e

                modifiers |= modifier

        try:
            key_or_button = getattr(glfw, f"KEY_{key_or_button_string}")
        except AttributeError:
            try:
                key_or_button = getattr(glfw, f"MOUSE_{key_or_button_string}")
            except AttributeError as e:
                raise SettingsError(
                    f"Unknown button or key '{key_or_button_string.lower()}'"
                ) from e

        return (modifiers, key_or_button)

    def _translate_bindings(self, bindings: Dict[str, str]) -> BindingsType:
        dictionary = {}
        for command, keys in bindings.items():
            try:
                dictionary_key = self._get_glfw_constants(keys)
            except SettingsError as e:
                logger.warning("Ignoring binding for %s: %s", command, str(e))

            # Issue a warning if the dictionary entry is about to be overwritten.
            if dictionary_key in dictionary:
                logger.warning(
                    "'%s' assigned to two commands: '%s' and '%s'. Assigning '%s' to '%s'",
                    keys,
                    dictionary[dictionary_key],
                    command,
                    keys,
                    command,
                )

            dictionary[dictionary_key] = command.split(".")

            logger.debug("Binding '%s' to '%s'", dictionary_key, command)

        return dictionary
