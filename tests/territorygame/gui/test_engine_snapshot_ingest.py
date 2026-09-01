from territorygame.api.move_result import MoveResult
from territorygame.domain.player_id import PlayerId
from territorygame.engine.game_snapshot import CellSnapshot, GameSnapshot
from territorygame.gui.game_window import ingest_engine_snapshot
from territorygame.gui.snapshot_history import SnapshotHistory


def _snapshot(last_move: MoveResult | None) -> GameSnapshot:
    player0 = PlayerId(0)
    cells = ((CellSnapshot(None, None),),)
    return GameSnapshot(1, 1, cells, (), player0, last_move, 3, False, None)


def test_snapshot_with_no_last_move_replaces_history():
    history: SnapshotHistory[GameSnapshot] = SnapshotHistory()
    after_turn = _snapshot(MoveResult.MOVED)
    after_reset = _snapshot(None)

    ingest_engine_snapshot(history, after_turn)
    ingest_engine_snapshot(history, after_reset)

    assert history.current() == after_reset
    assert not history.can_go_back()


def test_snapshot_after_a_move_appends_to_history():
    history: SnapshotHistory[GameSnapshot] = SnapshotHistory()
    first = _snapshot(None)
    second = _snapshot(MoveResult.MOVED)

    ingest_engine_snapshot(history, first)
    ingest_engine_snapshot(history, second)

    assert history.current() == second
    assert history.can_go_back()
