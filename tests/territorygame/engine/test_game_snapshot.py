from territorygame.api.grid_position import GridPosition
from territorygame.api.move_result import MoveResult
from territorygame.domain.player_id import PlayerId
from territorygame.engine.game_snapshot import CellSnapshot, GameSnapshot, PlayerSnapshot

player0 = PlayerId(0)


def _cells_with_one_owned_cell():
    rows = [[CellSnapshot(None, None) for _ in range(2)] for _ in range(2)]
    rows[0][0] = CellSnapshot(player0, None)
    return tuple(tuple(row) for row in rows)


def _build_snapshot(cells):
    return GameSnapshot(2, 2, cells, (), player0, MoveResult.MOVED, 3, False, None)


def test_cells_are_stored_as_immutable_tuples_no_defensive_copy_needed():
    # Java hand-writes a defensive deep-copy in its compact constructor
    # because Java arrays are mutable; Python tuples are immutable by
    # construction, so there's nothing to defend against.
    snapshot = _build_snapshot(_cells_with_one_owned_cell())
    assert isinstance(snapshot.cells, tuple)
    assert isinstance(snapshot.cells[0], tuple)
    assert snapshot.cells[0][0].territory_owner == player0


def test_equal_snapshots_with_different_cell_tuple_instances_are_equal():
    a = _build_snapshot(_cells_with_one_owned_cell())
    b = _build_snapshot(_cells_with_one_owned_cell())

    assert a == b
    assert hash(a) == hash(b)


def test_snapshots_with_different_cells_are_not_equal():
    empty = tuple(tuple(CellSnapshot(None, None) for _ in range(2)) for _ in range(2))
    a = _build_snapshot(_cells_with_one_owned_cell())
    b = _build_snapshot(empty)

    assert a != b


def test_player_snapshot_score_combines_territory_and_kills_with_a_bonus():
    player = PlayerSnapshot(player0, GridPosition(0, 0), 5, 2, 0, 10, (), None)

    assert player.score() == 25  # 5 territory + 2 kills * 10
