"""Simplest baseline controller: picks uniformly among directions that are
mechanically valid (in bounds, not onto the opponent's agent). Does not
avoid its own trail, so it can legitimately kill itself. Not really a
state machine — no persistent decision state, just a random pick each
turn — the name just matches the other examples for consistency."""

import random

from territorygame.api.agent_controller import AgentController
from territorygame.api.game_api import GameApi
from territorygame.helpers.movement_utils import random_direction, valid_directions


class RandomStateMachine(AgentController):
    def __init__(self) -> None:
        self._random = random.Random(7)

    def take_turn(self, game: GameApi) -> None:
        valid = valid_directions(game)
        choice = valid[self._random.randrange(len(valid))] if valid else random_direction(self._random)
        game.move(choice)
