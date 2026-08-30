"""Pure, stateless helpers for reasoning about movement and board bounds."""

import random

from territorygame.api.direction import Direction
from territorygame.api.game_api import GameApi
from territorygame.api.grid_position import GridPosition
from territorygame.api.occupant_view import OccupantView
from territorygame.api.visible_cell import VisibleCell

_DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.NORTH: (0, -1),
    Direction.SOUTH: (0, 1),
    Direction.EAST: (1, 0),
    Direction.WEST: (-1, 0),
}


def next_position(position: GridPosition, direction: Direction) -> GridPosition:
    dx, dy = _DELTAS[direction]
    return GridPosition(position.x + dx, position.y + dy)


def is_within_board(position: GridPosition, width: int, height: int) -> bool:
    return 0 <= position.x < width and 0 <= position.y < height


def is_valid_board_move(position: GridPosition, direction: Direction, width: int, height: int) -> bool:
    return is_within_board(next_position(position, direction), width, height)


def manhattan_distance(a: GridPosition, b: GridPosition) -> int:
    """Grid (non-diagonal) distance between two positions."""
    return abs(a.x - b.x) + abs(a.y - b.y)


def is_valid_move(game: GameApi, direction: Direction) -> bool:
    """Checks the two mechanical invalid-move rules available before
    submission: board bounds and whether the adjacent destination is
    currently the opponent's agent. Makes no strategic decision and picks
    no alternative direction. Notably, still allows moving onto the
    player's own trail."""
    destination = next_position(game.get_agent_position(), direction)
    if not is_within_board(destination, game.get_board_width(), game.get_board_height()):
        return False
    # Visibility radius always covers adjacent cells, so an absent cell
    # here is unreachable in practice; bounds are already confirmed above.
    cell = find_cell(game.get_visible_grid(), destination)
    if cell is None:
        return True
    return cell.occupant != OccupantView.OPPONENT_AGENT


def find_cell(
    visible_grid: tuple[tuple[VisibleCell, ...], ...], position: GridPosition
) -> VisibleCell | None:
    """Finds the visible cell at an absolute position, if it's within the visible window."""
    for row in visible_grid:
        for cell in row:
            if cell.position == position:
                return cell
    return None


def valid_directions(game: GameApi) -> list[Direction]:
    """Directions that are mechanically valid right now: in bounds and not
    onto the opponent's agent. Still includes moves onto the player's own
    trail."""
    return [direction for direction in Direction if is_valid_move(game, direction)]


def random_direction(rng: random.Random) -> Direction:
    """Picks a uniformly random direction."""
    values = list(Direction)
    return values[rng.randrange(len(values))]
