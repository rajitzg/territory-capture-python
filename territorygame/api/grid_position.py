"""An absolute board coordinate. (0, 0) is top-left; x increases right,
y increases down."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GridPosition:
    x: int
    y: int
