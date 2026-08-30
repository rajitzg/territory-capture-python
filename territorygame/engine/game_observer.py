"""Notified after each turn with the latest match state. Never mutates it."""

from abc import ABC, abstractmethod

from territorygame.engine.game_snapshot import GameSnapshot


class GameObserver(ABC):
    @abstractmethod
    def on_game_state_changed(self, snapshot: GameSnapshot) -> None: ...
