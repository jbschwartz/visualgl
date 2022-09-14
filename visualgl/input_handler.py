import logging
from typing import Dict, List, Tuple

import glfw


class InputHandler:
    def __init__(self, controllers: List, bindings: Dict[str, str]):
        self.controllers = controllers
        self.bindings = self._translate_bindings(bindings)

    def get_command(self, input):
        return self.bindings.get(input)

    def _translate_bindings(self, bindings: Dict[str, str]) -> Dict[Tuple[int, int], str]:
        dictionary = {}
        for command, keys in bindings.items():
            *modules, method, argument = command.split(".")

            modifier, key = self._glfw_constants(keys[:-1], key[-1])

            # for modifier

            modifiers = [
                getattr(
                    glfw,
                )
            ]

            if module in self.controllers:
                dictionary[(modifiers, key)] = (module.resolve(modules, method), argument)

    def _get_glfw_constants(self, keys: str) -> Tuple[int, int]:
        *modifiers, key = keys.replace(" ", "").split("+")

        if len(modifiers) > 0:
            # Confirm that all modifiers are valid
            modifier = 0
        else:
            modifier = 0

        key = getattr(glfw, f"KEY_{key.upper()}")

        return (modifier, key)
