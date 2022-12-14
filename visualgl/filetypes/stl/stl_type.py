import enum


@enum.unique
class STLType(enum.Enum):
    ASCII = enum.auto()
    BINARY = enum.auto()

    def __str__(self):
        return "ascii" if self is STLType.ASCII else "binary"

    def read_mode(self):
        return "r" if self is STLType.ASCII else "rb"

    def write_mode(self):
        return "w" if self is STLType.ASCII else "wb"
