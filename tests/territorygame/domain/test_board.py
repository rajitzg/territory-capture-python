from territorygame.api.grid_position import GridPosition
from territorygame.domain.board import Board
from territorygame.domain.player_id import PlayerId

player0 = PlayerId(0)
player1 = PlayerId(1)


def test_new_board_has_no_owners_anywhere():
    board = Board(5, 5)
    for y in range(5):
        for x in range(5):
            position = GridPosition(x, y)
            assert board.territory_owner_at(position) is None
            assert board.trail_owner_at(position) is None


def test_set_and_read_territory_owner():
    board = Board(5, 5)
    position = GridPosition(2, 2)

    board.set_territory_owner(position, player0)

    assert board.territory_owner_at(position) == player0


def test_cell_can_have_territory_owner_and_different_trail_owner_at_once():
    board = Board(5, 5)
    position = GridPosition(2, 2)

    board.set_territory_owner(position, player0)
    board.set_trail_owner(position, player1)

    assert board.territory_owner_at(position) == player0
    assert board.trail_owner_at(position) == player1


def test_territory_count_reflects_owned_cells():
    board = Board(5, 5)
    board.set_territory_owner(GridPosition(0, 0), player0)
    board.set_territory_owner(GridPosition(1, 0), player0)
    board.set_territory_owner(GridPosition(2, 0), player1)

    assert board.territory_count(player0) == 2
    assert board.territory_count(player1) == 1


def test_territory_of_returns_exact_owned_set():
    board = Board(5, 5)
    a = GridPosition(0, 0)
    b = GridPosition(1, 0)
    board.set_territory_owner(a, player0)
    board.set_territory_owner(b, player0)

    assert board.territory_of(player0) == {a, b}


def test_reassigning_territory_owner_updates_both_old_and_new_counts():
    board = Board(5, 5)
    position = GridPosition(0, 0)
    board.set_territory_owner(position, player0)

    board.set_territory_owner(position, player1)

    assert board.territory_count(player0) == 0
    assert board.territory_count(player1) == 1


def test_clear_all_territory_of_removes_only_that_players_cells():
    board = Board(5, 5)
    a = GridPosition(0, 0)
    b = GridPosition(1, 0)
    board.set_territory_owner(a, player0)
    board.set_territory_owner(b, player1)

    board.clear_all_territory_of(player0)

    assert board.territory_owner_at(a) is None
    assert board.territory_owner_at(b) == player1


def test_is_within_bounds_rejects_negative_and_out_of_range_coordinates():
    board = Board(5, 5)

    assert board.is_within_bounds(GridPosition(0, 0))
    assert board.is_within_bounds(GridPosition(4, 4))
    assert not board.is_within_bounds(GridPosition(-1, 0))
    assert not board.is_within_bounds(GridPosition(5, 0))
    assert not board.is_within_bounds(GridPosition(0, 5))
