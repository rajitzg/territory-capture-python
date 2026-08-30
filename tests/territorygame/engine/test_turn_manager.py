from territorygame.api.agent_controller import AgentController
from territorygame.api.direction import Direction
from territorygame.api.grid_position import GridPosition
from territorygame.domain.player_id import PlayerId
from territorygame.engine.game_api_impl import GameApiImpl
from territorygame.engine.turn_manager import TurnManager
from territorygame.rules.move_resolver import MoveResolver
from territorygame.rules.respawn_service import RespawnService
from territorygame.rules.territory_resolver import TerritoryResolver
from territorygame.visibility.visibility_service import VisibilityService
from tests.territorygame.test_games import two_player_state

player0 = PlayerId(0)
player1 = PlayerId(1)
turn_manager = TurnManager(20)


def _build_apis(state):
    move_resolver = MoveResolver(RespawnService(), TerritoryResolver())
    visibility_service = VisibilityService(5)
    return {
        player0: GameApiImpl(state, player0, move_resolver, visibility_service),
        player1: GameApiImpl(state, player1, move_resolver, visibility_service),
    }


class AlwaysMoveController(AgentController):
    """Always moves the same direction."""

    def __init__(self, direction: Direction) -> None:
        self._direction = direction

    def take_turn(self, game) -> None:
        game.move(self._direction)


class RetryOnceThenEastController(AgentController):
    """Tries an invalid move once, then always moves EAST after that."""

    def __init__(self) -> None:
        self.tried_invalid_move = False
        self.invocation_count = 0

    def take_turn(self, game) -> None:
        self.invocation_count += 1
        if not self.tried_invalid_move:
            self.tried_invalid_move = True
            game.move(Direction.NORTH)  # agent starts at y=0, guaranteed invalid
        else:
            game.move(Direction.EAST)


class AlwaysInvalidController(AgentController):
    """Always attempts an out-of-bounds move; never succeeds."""

    def __init__(self) -> None:
        self.invocation_count = 0

    def take_turn(self, game) -> None:
        self.invocation_count += 1
        game.move(Direction.NORTH)  # player0 starts at y=0 in these tests, guaranteed invalid


class ThrowingController(AgentController):
    """Always throws instead of moving."""

    def take_turn(self, game) -> None:
        raise RuntimeError("boom")


def test_active_player_alternates_after_each_turn():
    state = two_player_state(
        8, 8, GridPosition(1, 1), [GridPosition(1, 1)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )
    controllers = {player0: AlwaysMoveController(Direction.EAST), player1: AlwaysMoveController(Direction.WEST)}
    apis = _build_apis(state)

    assert state.get_active_player_id() == player0

    turn_manager.execute_turn(state, controllers, apis)
    assert state.get_active_player_id() == player1

    turn_manager.execute_turn(state, controllers, apis)
    assert state.get_active_player_id() == player0


def test_controller_is_invoked_again_after_an_invalid_move_within_the_same_turn():
    state = two_player_state(
        8, 8, GridPosition(0, 0), [GridPosition(0, 0)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )
    player0_controller = RetryOnceThenEastController()
    controllers = {player0: player0_controller, player1: AlwaysMoveController(Direction.WEST)}
    apis = _build_apis(state)

    turn_manager.execute_turn(state, controllers, apis)

    assert player0_controller.invocation_count >= 2
    # Only the one successful move (turn 2) decremented the turn count.
    assert state.get_remaining_turns(player0) == 9


def test_only_the_active_players_remaining_turns_are_consumed():
    state = two_player_state(
        8, 8, GridPosition(1, 1), [GridPosition(1, 1)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )
    controllers = {player0: AlwaysMoveController(Direction.EAST), player1: AlwaysMoveController(Direction.WEST)}
    apis = _build_apis(state)

    turn_manager.execute_turn(state, controllers, apis)

    assert state.get_remaining_turns(player0) == 9
    assert state.get_remaining_turns(player1) == 10


def test_turn_is_forfeited_after_max_attempts_when_controller_never_succeeds():
    state = two_player_state(
        8, 8, GridPosition(0, 0), [GridPosition(0, 0)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )
    capped_turn_manager = TurnManager(5)
    player0_controller = AlwaysInvalidController()
    controllers = {player0: player0_controller, player1: AlwaysMoveController(Direction.WEST)}
    apis = _build_apis(state)

    capped_turn_manager.execute_turn(state, controllers, apis)

    assert player0_controller.invocation_count == 5
    assert state.get_remaining_turns(player0) == 9  # forfeited turn is still consumed
    assert state.get_active_player_id() == player1
    assert state.get_last_turn_error() is not None


def test_turn_is_forfeited_when_controller_throws():
    state = two_player_state(
        8, 8, GridPosition(1, 1), [GridPosition(1, 1)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )
    controllers = {player0: ThrowingController(), player1: AlwaysMoveController(Direction.WEST)}
    apis = _build_apis(state)

    turn_manager.execute_turn(state, controllers, apis)

    assert state.get_remaining_turns(player0) == 9
    assert state.get_active_player_id() == player1
    assert state.get_last_turn_error() is not None
