"""A candidate-side memory of previously observed cells. Stores only the
latest value seen for each cell; never infers changes to cells that
haven't been re-observed."""

from territorygame.api.grid_position import GridPosition
from territorygame.api.visible_cell import VisibleCell
from territorygame.helpers.movement_utils import is_within_board


class ObservedBoard:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._observed: list[list[VisibleCell | None]] = [
            [None for _ in range(width)] for _ in range(height)
        ]

    def update(self, visible_grid: tuple[tuple[VisibleCell, ...], ...]) -> None:
        for row in visible_grid:
            for cell in row:
                position = cell.position
                self._observed[position.y][position.x] = cell

    def get(self, position: GridPosition) -> VisibleCell | None:
        if not is_within_board(position, self._width, self._height):
            return None
        return self._observed[position.y][position.x]

    def has_observed(self, position: GridPosition) -> bool:
        return (
            is_within_board(position, self._width, self._height)
            and self._observed[position.y][position.x] is not None
        )

    def clear(self) -> None:
        for row in self._observed:
            for x in range(len(row)):
                row[x] = None
