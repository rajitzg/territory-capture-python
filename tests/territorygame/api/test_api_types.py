from territorygame.api.direction import Direction
from territorygame.api.grid_position import GridPosition
from territorygame.api.move_result import MoveResult
from territorygame.api.occupant_view import OccupantView
from territorygame.api.territory_view import TerritoryView
from territorygame.api.visible_cell import VisibleCell


def test_direction_has_four_cardinal_members():
    assert {d.name for d in Direction} == {"NORTH", "SOUTH", "EAST", "WEST"}


def test_move_result_has_four_outcomes():
    assert {r.name for r in MoveResult} == {"MOVED", "CAPTURED", "DIED", "INVALID"}


def test_grid_position_is_a_value_type():
    a = GridPosition(3, 4)
    b = GridPosition(3, 4)
    assert a == b
    assert hash(a) == hash(b)
    assert a.x == 3
    assert a.y == 4


def test_grid_position_is_frozen():
    position = GridPosition(1, 1)
    try:
        position.x = 2
        assert False, "expected FrozenInstanceError"
    except AttributeError:
        pass


def test_visible_cell_is_a_value_type():
    position = GridPosition(2, 2)
    a = VisibleCell(position, OccupantView.SELF_AGENT, TerritoryView.SELF)
    b = VisibleCell(GridPosition(2, 2), OccupantView.SELF_AGENT, TerritoryView.SELF)
    assert a == b
