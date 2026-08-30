"""Strategy a player supplies to play the game. The framework invokes
take_turn(game) repeatedly for the same turn until a successful move is made."""

from abc import ABC, abstractmethod

from territorygame.api.game_api import GameApi


class AgentController(ABC):

    @abstractmethod
    def take_turn(self, game: GameApi) -> None: ...

    def get_debug_state(self) -> str | None:
        """Optional label for whatever internal state this controller considers
        itself to be in right now (e.g. an enum's name), shown next to it in the
        GUI. Purely for observing a match; has no effect on gameplay. Returns
        None (the default) if there's nothing worth showing."""
        return None
