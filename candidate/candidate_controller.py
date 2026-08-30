# Replace this stub with your own implementation. See CANDIDATE_GUIDE.md
# for the game rules, the GameApi surface, and the helpers you're given.

from territorygame.api.agent_controller import AgentController
from territorygame.api.direction import Direction
from territorygame.api.game_api import GameApi
from territorygame.helpers.movement_utils import is_valid_move


class CandidateController(AgentController):
    def take_turn(self, game: GameApi) -> None:
        if is_valid_move(game, Direction.EAST):
            game.move(Direction.EAST)
        else:
            game.move(Direction.NORTH)
