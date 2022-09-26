import enum
import inspect
from typing import Any, Callable, Type, Union, get_args, get_origin

from visualgl.window import InputEvent

from .exceptions import ControllerError

_COMMAND_HANDLER_ATTRIBUTE = "_is_handler"


def _convert_parameter_to_annotated_type(parameter_type: Type, value: str) -> Any:
    """Return the provided parameter value converted to the provided parameter type.

    If the conversion fails, raise a ControllerError.
    """
    if value is None:
        return None

    # If there is no annotation, there is nothing to do.
    if parameter_type is inspect.Parameter.empty:
        return value

    # See if the annotation is `Optional`.
    if get_origin(parameter_type) is Union:
        union_arguments = get_args(parameter_type)

        # This could be made more sophisticated where it could try to convert each type
        # until one succeeds. But that's probably overkill; only support `Optional` type
        # annotations.
        assert len(union_arguments) == 2 and union_arguments[-1] is type(None)

        parameter_type = union_arguments[0]

    # If the value is already the correct type, there is nothing to do. This can happen in the case
    # where the method is called externally (without an `InputEvent`)
    if isinstance(value, parameter_type):
        return value

    try:
        # Enums need brackets to initialize from a name so handle them explicitly.
        if issubclass(parameter_type, enum.Enum):
            # Note that it is assumed that enum names will be all upper case since they represent
            # constants.
            return parameter_type[value.upper()]

        return parameter_type(value)
    except (KeyError, TypeError) as e:
        raise ControllerError(f"Cannot convert parameter '{value}' to {parameter_type}") from e


def command(handler: Callable) -> Callable:
    """Decorate a `Controller` method with an attribute indicating it is a command handler.

    This decorator is an adapter that will unpack `InputEvent` attributes passed into the `event`
    keyword argument onto the handler method's arguments. For example:

    ```
    @command
    def on_click(cursor_position: Vector3) -> None:
        ...
    ```

    Can be called as: `controller.on_click(event=event)`. This facilitates automatic routing of
    `InputEvent`s (see `Controller.command`). Note that the handler argument names must match
    `InputEvent` attributes in order for the mapping to work.

    Signatures of the command handlers are thus explicit about what arguments they need. Instead
    of taking an `InputEvent`, the signature becomes self-documenting. Further, the methods can be
    easily called by other external callers without needing to construct an `InputEvent`.

    This decorator will also use the arguments type annotations and attempt to convert the argument
    (which is typically a string which comes from `CommandRoute`) to the annotated type.
    """
    parameters = inspect.signature(handler).parameters.items()

    def wrapper(*args, event=None, **kwargs):
        args = list(args)

        new_args = []
        # For each parameter in the handlers signature, look for the matching attribute on
        # `InputEvent`. If that doesn't exist, take the positional arguments in order and convert
        # their types, if necessary and possible.
        for name, param in parameters:
            if hasattr(event, name):
                new_args.append(getattr(event, name))
            else:
                new_args.append(_convert_parameter_to_annotated_type(param.annotation, args.pop(0)))

        return handler(*new_args, **kwargs)

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
