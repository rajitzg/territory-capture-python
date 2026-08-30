from territorygame.api.grid_position import GridPosition
from territorygame.api.occupant_view import OccupantView
from territorygame.api.territory_view import TerritoryView
from territorygame.api.visible_cell import VisibleCell
from territorygame.helpers.observed_board import ObservedBoard


def test_unobserved_cell_has_no_value():
    board = ObservedBoard(5, 5)
    position = GridPosition(1, 1)

    assert not board.has_observed(position)
    assert board.get(position) is None


def test_update_stores_latest_value_per_cell():
    board = ObservedBoard(5, 5)
    position = GridPosition(1, 1)
    stored = VisibleCell(position, OccupantView.EMPTY, TerritoryView.SELF)

    board.update(((stored,),))

    assert board.has_observed(position)
    assert board.get(position) == stored


def test_later_update_overwrites_earlier_value_for_same_cell():
    board = ObservedBoard(5, 5)
    position = GridPosition(1, 1)
    later = VisibleCell(position, OccupantView.EMPTY, TerritoryView.OPPONENT)

    board.update(((VisibleCell(position, OccupantView.EMPTY, TerritoryView.UNOWNED),),))
    board.update(((later,),))

    assert board.get(position) == later


def test_update_does_not_affect_cells_outside_the_given_grid():
    board = ObservedBoard(5, 5)
    observed = GridPosition(1, 1)
    untouched = GridPosition(3, 3)
    board.update(((VisibleCell(observed, OccupantView.EMPTY, TerritoryView.SELF),),))

    assert not board.has_observed(untouched)


def test_clear_forgets_all_previously_observed_cells():
    board = ObservedBoard(5, 5)
    position = GridPosition(1, 1)
    board.update(((VisibleCell(position, OccupantView.EMPTY, TerritoryView.SELF),),))

    board.clear()

    assert not board.has_observed(position)


def test_get_returns_none_for_out_of_bounds_position():
    board = ObservedBoard(5, 5)

    assert board.get(GridPosition(-1, 0)) is None
    assert not board.has_observed(GridPosition(10, 10))
