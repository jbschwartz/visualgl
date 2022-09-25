import inspect
from typing import Any, Callable

from visualgl.window import InputEvent

from .exceptions import ControllerError

_COMMAND_HANDLER_ATTRIBUTE = "_is_handler"


def command(method: Callable) -> Callable:
    """Decorate a Controller method with an attribute indicating it is a command endpoint.

    This decorator will also unpack parameters from an event passed into the `event` keyword
    argument. This allows the signatures of the command handlers to be explicit about what they need
    (instead of just taking an InputEvent).
    """
    method_parameters = inspect.signature(method).parameters.keys()

    def wrapper(*args, event=None, **kwargs):
        if not event:
            return method(*args, **kwargs)

        new_args = []
        index = 0
        for method_parameter in method_parameters:
            if hasattr(event, method_parameter):
                new_args.append(getattr(event, method_parameter))
            else:
                new_args.append(args[index])
                index += 1

        return method(*new_args, **kwargs)

    setattr(wrapper, _COMMAND_HANDLER_ATTRIBUTE, True)
    return wrapper


# pylint: disable=too-few-public-methods
class Controller:
    """Base class responsible for handling commands.

    This class should be overridden with a concrete implementation. For every command, the child
    class should have a `@command` decorated method.
    """

    def command(self, event: InputEvent) -> Any:
        """Call the command associated with the given input event."""
        if method := getattr(self, event.command.method, None):
            # This prevents the user from being able to call any command on a handler even if they
            # are not supposed to.
            if hasattr(method, _COMMAND_HANDLER_ATTRIBUTE):
                return method(event.command.parameter, event=event)

        raise ControllerError(
            f"No command handler for '{event.command.method}' found in the "
            f"{event.command.controller} controller. "
        )
