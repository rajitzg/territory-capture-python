import queue

from territorygame.api.agent_controller import AgentController
from territorygame.api.direction import Direction
from territorygame.api.grid_position import GridPosition
from territorygame.domain.game_config import GameConfig
from territorygame.engine.game_engine import GameEngine
from territorygame.engine.game_observer import GameObserver

_POLL_TIMEOUT_SECONDS = 2


class AlwaysMoveController(AgentController):
    def __init__(self, direction: Direction) -> None:
        self._direction = direction

    def take_turn(self, game) -> None:
        game.move(self._direction)


class QueueObserver(GameObserver):
    """Test double: pushes every snapshot onto a queue so the test can poll
    it, mirroring the Java test's use of a BlockingQueue + method reference."""

    def __init__(self, snapshots: "queue.Queue") -> None:
        self._snapshots = snapshots

    def on_game_state_changed(self, snapshot) -> None:
        self._snapshots.put(snapshot)


def _poll_snapshot(snapshots: "queue.Queue"):
    try:
        snapshot = snapshots.get(timeout=_POLL_TIMEOUT_SECONDS)
    except queue.Empty:
        snapshot = None
    assert snapshot is not None, "expected an observer notification within 2 seconds"
    return snapshot


def test_match_runs_to_completion_with_alternating_turns_and_correct_final_counts():
    config = GameConfig(8, 8, 5, 2, [GridPosition(1, 1), GridPosition(6, 6)], 1, 0, 20, [1, 2])
    controllers = [AlwaysMoveController(Direction.EAST), AlwaysMoveController(Direction.WEST)]
    engine = GameEngine(config, controllers)
    snapshots: "queue.Queue" = queue.Queue()
    engine.add_observer(QueueObserver(snapshots))
    engine.reset(controllers)

    initial = _poll_snapshot(snapshots)
    assert not initial.game_over

    engine.start()

    last = None
    for _ in range(4):  # 2 turns per player, 2 players
        last = _poll_snapshot(snapshots)

    assert last.game_over
    for player in last.players:
        assert player.remaining_turns == 0
        assert player.territory_count == 1  # neither move returned home to capture


def test_step_runs_exactly_one_turn():
    config = GameConfig(8, 8, 5, 10, [GridPosition(1, 1), GridPosition(6, 6)], 1, 0, 20, [1, 2])
    controllers = [AlwaysMoveController(Direction.EAST), AlwaysMoveController(Direction.WEST)]
    engine = GameEngine(config, controllers)
    snapshots: "queue.Queue" = queue.Queue()
    engine.add_observer(QueueObserver(snapshots))
    engine.reset(controllers)
    _poll_snapshot(snapshots)  # initial

    engine.step()
    after_one_step = _poll_snapshot(snapshots)

    # Only player0 (the first active player) should have moved.
    assert after_one_step.players[0].remaining_turns == 9
    assert after_one_step.players[1].remaining_turns == 10
    assert after_one_step.active_player_id == after_one_step.players[1].id


def test_reset_with_new_controllers_replaces_the_previous_ones():
    config = GameConfig(8, 8, 5, 10, [GridPosition(1, 1), GridPosition(6, 6)], 1, 0, 20, [1, 2])
    initial_controllers = [AlwaysMoveController(Direction.EAST), AlwaysMoveController(Direction.WEST)]
    engine = GameEngine(config, initial_controllers)
    snapshots: "queue.Queue" = queue.Queue()
    engine.add_observer(QueueObserver(snapshots))
    engine.reset(initial_controllers)
    _poll_snapshot(snapshots)

    new_controllers = [AlwaysMoveController(Direction.SOUTH), AlwaysMoveController(Direction.NORTH)]
    engine.reset(new_controllers)
    after_reset = _poll_snapshot(snapshots)
    assert not after_reset.game_over

    engine.step()
    after_step = _poll_snapshot(snapshots)

    # Player0 started at (1,1); with the new controllers it should have moved
    # SOUTH to (1,2), not EAST to (2,1).
    assert after_step.players[0].position == GridPosition(1, 2)
