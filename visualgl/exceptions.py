class VisualError(Exception):
    pass


class SettingsError(VisualError):
    """Raised when a setting is invalid."""


class ControllerError(VisualError):
    """Raised when an error occurs when attempting to handle a command on a controller."""


class ParserError(VisualError):
    def __init__(self, line, msg):
        self.line = line
        super().__init__(msg)


class STLNotATriangle(ParserError):
    def __init__(self, line, num_vertices):
        ParserError.__init__(
            self, line, f"Facet must be a triangle ({num_vertices} vertices provided)"
        )


class STLStateError(ParserError):
    def __init__(self, line, expected_state, actual_state):
        ParserError.__init__(
            self, line, f"Unexpected `{actual_state}` when looking for `{expected_state}`"
        )


class STLUnexpectedSize(ParserError):
    def __init__(self, line, keyword):
        ParserError.__init__(self, line, f"Unexpected `{keyword}` size")


class STLFloatError(ParserError):
    def __init__(self, line, keyword):
        ParserError.__init__(self, line, f"`{keyword}` component cannot be converted to float")
