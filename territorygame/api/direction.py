"""The four cardinal movement directions an agent can take."""

from enum import Enum, auto


class Direction(Enum):
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()
