"""Outcome of a single GameApi.move(direction) call."""

from enum import Enum, auto


class MoveResult(Enum):
    MOVED = auto()
    CAPTURED = auto()
    DIED = auto()
    INVALID = auto()
