"""Applies capture effects when a player's trail closes: converting the
trail to territory and flood-filling only the region that trail newly
encloses. Existing holes in the capturer's territory (for example an
opponent island created by respawn) are left untouched."""

from collections import deque

from territorygame.api.direction import Direction
from territorygame.api.grid_position import GridPosition
from territorygame.domain.board import Board
from territorygame.domain.game_state import GameState
from territorygame.domain.player_id import PlayerId
from territorygame.helpers.movement_utils import is_within_board, next_position


class TerritoryResolver:
    def apply_capture(self, state: GameState, capturer_id: PlayerId) -> None:
        board = state.get_board()
        capturer = state.get_player(capturer_id)
        agent = capturer.get_agent()

        already_enclosed = set(self._find_enclosed_cells(board, capturer_id))

        trail = agent.get_active_trail()
        for cell in trail:
            board.set_territory_owner(cell, capturer_id)
            board.set_trail_owner(cell, None)

        for enclosed_cell in self._find_enclosed_cells(board, capturer_id):
            if enclosed_cell not in already_enclosed:
                board.set_territory_owner(enclosed_cell, capturer_id)

        agent.clear_trail()

    def _find_enclosed_cells(self, board: Board, capturer_id: PlayerId) -> list[GridPosition]:
        width = board.get_width()
        height = board.get_height()
        reached_from_edge = [[False] * width for _ in range(height)]
        frontier: deque[GridPosition] = deque()

        for x in range(width):
            self._seed_if_outside_territory(board, capturer_id, GridPosition(x, 0), reached_from_edge, frontier)
            self._seed_if_outside_territory(
                board, capturer_id, GridPosition(x, height - 1), reached_from_edge, frontier
            )
        for y in range(height):
            self._seed_if_outside_territory(board, capturer_id, GridPosition(0, y), reached_from_edge, frontier)
            self._seed_if_outside_territory(
                board, capturer_id, GridPosition(width - 1, y), reached_from_edge, frontier
            )

        while frontier:
            current = frontier.popleft()
            for neighbor in self._cardinal_neighbors(current, width, height):
                if not reached_from_edge[neighbor.y][neighbor.x] and board.territory_owner_at(neighbor) != capturer_id:
                    reached_from_edge[neighbor.y][neighbor.x] = True
                    frontier.append(neighbor)

        enclosed = []
        for y in range(height):
            for x in range(width):
                position = GridPosition(x, y)
                if not reached_from_edge[y][x] and board.territory_owner_at(position) != capturer_id:
                    enclosed.append(position)
        return enclosed

    @staticmethod
    def _seed_if_outside_territory(board, capturer_id, position, reached_from_edge, frontier) -> None:
        if board.territory_owner_at(position) != capturer_id and not reached_from_edge[position.y][position.x]:
            reached_from_edge[position.y][position.x] = True
            frontier.append(position)

    @staticmethod
    def _cardinal_neighbors(position: GridPosition, width: int, height: int) -> list[GridPosition]:
        neighbors = []
        for direction in Direction:
            neighbor = next_position(position, direction)
            if is_within_board(neighbor, width, height):
                neighbors.append(neighbor)
        return neighbors
