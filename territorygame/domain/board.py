"""Authoritative board-cell state. Agent positions are not tracked here; they
live on Agent and are considered separately by callers doing occupancy
checks."""

from territorygame.api.grid_position import GridPosition
from territorygame.domain.board_cell import BoardCell
from territorygame.domain.player_id import PlayerId
from territorygame.helpers.movement_utils import is_within_board


class Board:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._cells: list[list[BoardCell]] = [
            [BoardCell() for _ in range(width)] for _ in range(height)
        ]

    def get_width(self) -> int:
        return self._width

    def get_height(self) -> int:
        return self._height

    def is_within_bounds(self, position: GridPosition) -> bool:
        return is_within_board(position, self._width, self._height)

    def territory_owner_at(self, position: GridPosition) -> PlayerId | None:
        return self._cell_at(position).get_territory_owner()

    def trail_owner_at(self, position: GridPosition) -> PlayerId | None:
        return self._cell_at(position).get_trail_owner()

    def set_territory_owner(self, position: GridPosition, owner: PlayerId | None) -> None:
        self._cell_at(position).set_territory_owner(owner)

    def set_trail_owner(self, position: GridPosition, owner: PlayerId | None) -> None:
        self._cell_at(position).set_trail_owner(owner)

    def territory_count(self, owner: PlayerId) -> int:
        count = 0
        for y in range(self._height):
            for x in range(self._width):
                if self._cells[y][x].get_territory_owner() == owner:
                    count += 1
        return count

    def territory_of(self, owner: PlayerId) -> set[GridPosition]:
        positions: set[GridPosition] = set()
        for y in range(self._height):
            for x in range(self._width):
                if self._cells[y][x].get_territory_owner() == owner:
                    positions.add(GridPosition(x, y))
        return positions

    def clear_all_territory_of(self, owner: PlayerId) -> None:
        for position in self.territory_of(owner):
            self.set_territory_owner(position, None)

    def _cell_at(self, position: GridPosition) -> BoardCell:
        if not self.is_within_bounds(position):
            raise ValueError(f"Position out of bounds: {position}")
        return self._cells[position.y][position.x]
