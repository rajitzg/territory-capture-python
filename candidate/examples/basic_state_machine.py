"""Deliberately weak reference implementation. It demonstrates persistent
controller state, state transitions, calling move(), and reacting to
MoveResult — not a strategy worth copying. EXPANDING still wanders
randomly and can walk over its own trail; RETURNING avoids its own trail
when it can, but only steps around it, not toward the nearest owned
territory. See README.md's Tips section for ideas (finding your nearest
territory, tracking the opponent, etc.) left undone here."""

import random
from enum import Enum, auto

from territorygame.api.agent_controller import AgentController
from territorygame.api.direction import Direction
from territorygame.api.game_api import GameApi
from territorygame.api.move_result import MoveResult
from territorygame.api.occupant_view import OccupantView
from territorygame.helpers.movement_utils import is_valid_move, next_position, random_direction, valid_directions

_RETURN_TRAIL_THRESHOLD = 4


class _State(Enum):
    EXPANDING = auto()
    RETURNING = auto()


class BasicStateMachine(AgentController):
    def __init__(self) -> None:
        self._state = _State.EXPANDING
        self._random = random.Random(42)

    def take_turn(self, game: GameApi) -> None:
        if self._state == _State.EXPANDING:
            direction = self._pick_expanding_direction(game)
        else:
            direction = self._pick_returning_direction(game)

        result = game.move(direction)
        self._update_state(game, result)

    def get_debug_state(self) -> str | None:
        return self._state.name

    def _update_state(self, game: GameApi, result: MoveResult) -> None:
        if result in (MoveResult.CAPTURED, MoveResult.DIED):
            self._state = _State.EXPANDING
            return
        if self._state == _State.EXPANDING and len(game.get_active_trail()) >= _RETURN_TRAIL_THRESHOLD:
            self._state = _State.RETURNING
        elif self._state == _State.RETURNING and not game.get_active_trail():
            self._state = _State.EXPANDING

    def _pick_expanding_direction(self, game: GameApi) -> Direction:
        """Wanders randomly among the mechanically safe directions."""
        safe_directions = valid_directions(game)
        if not safe_directions:
            return random_direction(self._random)
        return safe_directions[self._random.randrange(len(safe_directions))]

    def _pick_returning_direction(self, game: GameApi) -> Direction:
        """Heads toward the respawn point one axis at a time; not
        necessarily the nearest owned cell."""
        position = game.get_agent_position()
        home = game.get_respawn_position()

        if position.x < home.x:
            preferred = Direction.EAST
        elif position.x > home.x:
            preferred = Direction.WEST
        elif position.y < home.y:
            preferred = Direction.SOUTH
        elif position.y > home.y:
            preferred = Direction.NORTH
        else:
            preferred = random_direction(self._random)

        if self._is_safe_move(game, preferred):
            return preferred

        # Preferred direction would cross our own trail: try any other
        # direction that avoids it before accepting that risk.
        for direction in Direction:
            if self._is_safe_move(game, direction):
                return direction

        # Nothing avoids our own trail — take the mechanically valid move anyway.
        if is_valid_move(game, preferred):
            return preferred
        return random_direction(self._random)

    @staticmethod
    def _is_safe_move(game: GameApi, direction: Direction) -> bool:
        """Mechanically valid and not a step onto our own trail."""
        if not is_valid_move(game, direction):
            return False
        destination = next_position(game.get_agent_position(), direction)
        for row in game.get_visible_grid():
            for cell in row:
                if cell.position == destination:
                    return cell.occupant != OccupantView.SELF_TRAIL
        return True
