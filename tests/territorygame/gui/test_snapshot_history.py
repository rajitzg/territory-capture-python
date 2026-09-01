from territorygame.gui.snapshot_history import SnapshotHistory


def test_recorded_snapshot_becomes_current():
    history: SnapshotHistory[str] = SnapshotHistory()
    history.record("initial")
    assert history.current() == "initial"


def test_back_shows_the_previous_snapshot():
    history: SnapshotHistory[str] = SnapshotHistory()
    history.record("first")
    history.record("second")
    history.back()
    assert history.current() == "first"


def test_back_at_the_start_stays_on_the_first_snapshot():
    history: SnapshotHistory[str] = SnapshotHistory()
    history.record("only")
    history.back()
    assert history.current() == "only"


def test_forward_after_back_returns_toward_live():
    history: SnapshotHistory[str] = SnapshotHistory()
    history.record("first")
    history.record("second")
    history.back()
    history.forward()
    assert history.current() == "second"


def test_recording_while_reviewing_jumps_to_the_new_live_snapshot():
    history: SnapshotHistory[str] = SnapshotHistory()
    history.record("first")
    history.record("second")
    history.record("third")
    history.back()
    history.back()
    history.record("fourth")
    assert history.current() == "fourth"


def test_clear_discards_history_so_the_next_record_is_current():
    history: SnapshotHistory[str] = SnapshotHistory()
    history.record("old")
    history.clear()
    history.record("fresh")
    assert history.current() == "fresh"


def test_can_go_back_and_forward_track_the_cursor():
    history: SnapshotHistory[str] = SnapshotHistory()
    history.record("first")
    history.record("second")
    assert not history.can_go_forward()
    assert history.can_go_back()
    history.back()
    assert history.can_go_forward()
    assert not history.can_go_back()


def test_is_at_live_until_the_user_steps_back():
    history: SnapshotHistory[str] = SnapshotHistory()
    history.record("first")
    history.record("second")
    assert history.is_at_live()
    history.back()
    assert not history.is_at_live()
    history.forward()
    assert history.is_at_live()


def test_position_is_one_based_for_status_text():
    history: SnapshotHistory[str] = SnapshotHistory()
    history.record("first")
    history.record("second")
    history.record("third")
    assert history.position() == 3
    assert history.size() == 3
    history.back()
    assert history.position() == 2
    assert history.size() == 3


def _history_with(count: int) -> SnapshotHistory[str]:
    history: SnapshotHistory[str] = SnapshotHistory()
    for i in range(1, count + 1):
        history.record(f"s{i}")
    return history


def test_back_by_ten_moves_ten_snapshots():
    history = _history_with(15)
    history.back(10)
    assert history.current() == "s5"


def test_back_by_ten_clamps_at_the_start():
    history = _history_with(4)
    history.back(10)
    assert history.current() == "s1"


def test_forward_by_ten_moves_ten_snapshots():
    history = _history_with(15)
    history.back(14)
    history.forward(10)
    assert history.current() == "s11"


def test_forward_by_ten_clamps_at_live():
    history = _history_with(4)
    history.back(2)
    history.forward(10)
    assert history.current() == "s4"
