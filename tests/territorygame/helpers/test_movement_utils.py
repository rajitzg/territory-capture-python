import random

from territorygame.api.direction import Direction
from territorygame.api.game_api import GameApi
from territorygame.api.grid_position import GridPosition
from territorygame.api.move_result import MoveResult
from territorygame.api.occupant_view import OccupantView
from territorygame.api.territory_view import TerritoryView
from territorygame.api.visible_cell import VisibleCell
from territorygame.helpers import movement_utils


class StubGameApi(GameApi):
    """Minimal GameApi test double exposing only what movement_utils reads."""

    def __init__(self, position, width, height, visible_grid):
        self._position = position
        self._width = width
        self._height = height
        self._visible_grid = visible_grid

    def get_agent_position(self):
        return self._position

    def get_respawn_position(self):
        return self._position

    def get_owned_territory_cell_count(self):
        return 0

    def get_opponent_territory_cell_count(self):
        return 0

    def get_remaining_turns(self):
        return 0

    def get_active_trail(self):
        return []

    def get_visible_grid(self):
        return self._visible_grid

    def get_board_width(self):
        return self._width

    def get_board_height(self):
        return self._height

    def move(self, direction):
        return MoveResult.INVALID


def test_next_position_moves_one_cell_per_direction():
    start = GridPosition(5, 5)
    assert movement_utils.next_position(start, Direction.NORTH) == GridPosition(5, 4)
    assert movement_utils.next_position(start, Direction.SOUTH) == GridPosition(5, 6)
    assert movement_utils.next_position(start, Direction.EAST) == GridPosition(6, 5)
    assert movement_utils.next_position(start, Direction.WEST) == GridPosition(4, 5)


def test_is_within_board_checks_both_axes():
    assert movement_utils.is_within_board(GridPosition(0, 0), 5, 5)
    assert movement_utils.is_within_board(GridPosition(4, 4), 5, 5)
    assert not movement_utils.is_within_board(GridPosition(-1, 0), 5, 5)
    assert not movement_utils.is_within_board(GridPosition(5, 0), 5, 5)
    assert not movement_utils.is_within_board(GridPosition(0, 5), 5, 5)


def test_is_valid_board_move_checks_destination_bounds():
    assert movement_utils.is_valid_board_move(GridPosition(0, 0), Direction.EAST, 5, 5)
    assert not movement_utils.is_valid_board_move(GridPosition(0, 0), Direction.NORTH, 5, 5)
    assert not movement_utils.is_valid_board_move(GridPosition(0, 0), Direction.WEST, 5, 5)


def test_manhattan_distance_is_grid_distance():
    assert movement_utils.manhattan_distance(GridPosition(0, 0), GridPosition(3, 4)) == 7
    assert movement_utils.manhattan_distance(GridPosition(2, 2), GridPosition(2, 2)) == 0


def test_is_valid_move_rejects_out_of_bounds_without_needing_visible_grid():
    game = StubGameApi(GridPosition(0, 0), 5, 5, ())
    assert not movement_utils.is_valid_move(game, Direction.NORTH)


def test_is_valid_move_rejects_opponent_agent_cell():
    position = GridPosition(2, 2)
    opponent_at = GridPosition(3, 2)
    grid = ((VisibleCell(opponent_at, OccupantView.OPPONENT_AGENT, TerritoryView.UNOWNED),),)
    game = StubGameApi(position, 5, 5, grid)
    assert not movement_utils.is_valid_move(game, Direction.EAST)


def test_is_valid_move_accepts_free_in_bounds_cell():
    position = GridPosition(2, 2)
    destination = GridPosition(3, 2)
    grid = ((VisibleCell(destination, OccupantView.EMPTY, TerritoryView.UNOWNED),),)
    game = StubGameApi(position, 5, 5, grid)
    assert movement_utils.is_valid_move(game, Direction.EAST)


def test_find_cell_returns_the_cell_at_a_matching_position():
    target = GridPosition(3, 2)
    grid = ((VisibleCell(target, OccupantView.EMPTY, TerritoryView.OPPONENT),),)

    found = movement_utils.find_cell(grid, target)

    assert found is not None
    assert found.occupant == OccupantView.EMPTY
    assert found.territory == TerritoryView.OPPONENT


def test_find_cell_returns_none_when_position_is_not_in_the_grid():
    grid = ((VisibleCell(GridPosition(3, 2), OccupantView.EMPTY, TerritoryView.UNOWNED),),)
    assert movement_utils.find_cell(grid, GridPosition(9, 9)) is None


def test_valid_directions_excludes_out_of_bounds_and_opponent_agent_cells():
    position = GridPosition(0, 0)
    east = GridPosition(1, 0)
    south = GridPosition(0, 1)
    grid = (
        (
            VisibleCell(position, OccupantView.SELF_AGENT, TerritoryView.UNOWNED),
            VisibleCell(east, OccupantView.OPPONENT_AGENT, TerritoryView.UNOWNED),
        ),
        (
            VisibleCell(south, OccupantView.EMPTY, TerritoryView.UNOWNED),
            VisibleCell(GridPosition(1, 1), OccupantView.EMPTY, TerritoryView.UNOWNED),
        ),
    )
    game = StubGameApi(position, 5, 5, grid)

    valid = movement_utils.valid_directions(game)

    assert set(valid) == {Direction.SOUTH}


def test_random_direction_returns_one_of_the_four_directions():
    direction = movement_utils.random_direction(random.Random(1))
    assert direction in set(Direction)
