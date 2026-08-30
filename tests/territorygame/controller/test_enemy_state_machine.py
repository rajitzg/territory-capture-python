import queue

from territorygame.api.grid_position import GridPosition
from territorygame.controller.enemy_state_machine import EnemyStateMachine
from territorygame.domain.game_config import GameConfig
from territorygame.engine.game_engine import GameEngine
from territorygame.engine.game_observer import GameObserver


class QueueObserver(GameObserver):
    def __init__(self, snapshots: "queue.Queue") -> None:
        self._snapshots = snapshots

    def on_game_state_changed(self, snapshot) -> None:
        self._snapshots.put(snapshot)


def test_plays_many_turns_against_itself_without_framework_errors():
    config = GameConfig(20, 20, 11, 40, [GridPosition(4, 10), GridPosition(15, 10)], 3, 0, 20, [1001, 2002])
    controllers = [EnemyStateMachine(1001), EnemyStateMachine(2002)]
    engine = GameEngine(config, controllers)
    snapshots: "queue.Queue" = queue.Queue()
    engine.add_observer(QueueObserver(snapshots))
    engine.reset(controllers)
    assert snapshots.get(timeout=2) is not None

    engine.start()

    last = None
    for _ in range(80):  # 40 turns per player, 2 players
        snapshot = snapshots.get(timeout=2)
        assert snapshot is not None
        last = snapshot

    assert last.game_over
