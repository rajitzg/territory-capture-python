from territorygame.api.direction import Direction
from territorygame.api.grid_position import GridPosition
from territorygame.api.move_result import MoveResult
from territorygame.domain.player_id import PlayerId
from territorygame.engine.game_api_impl import GameApiImpl
from territorygame.rules.move_resolver import MoveResolver
from territorygame.rules.respawn_service import RespawnService
from territorygame.rules.territory_resolver import TerritoryResolver
from territorygame.visibility.visibility_service import VisibilityService
from tests.territorygame.test_games import two_player_state

player0 = PlayerId(0)


def _new_api(state):
    move_resolver = MoveResolver(RespawnService(), TerritoryResolver())
    return GameApiImpl(state, player0, move_resolver, VisibilityService(5))


def test_first_move_this_turn_resolves_normally():
    state = two_player_state(
        8, 8, GridPosition(1, 1), [GridPosition(1, 1)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )
    api = _new_api(state)
    api.reset_for_new_turn()

    result = api.move(Direction.EAST)

    assert result == MoveResult.MOVED


def test_second_successful_move_in_the_same_turn_is_rejected():
    state = two_player_state(
        8, 8, GridPosition(1, 1), [GridPosition(1, 1)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )
    api = _new_api(state)
    api.reset_for_new_turn()

    api.move(Direction.EAST)
    second_result = api.move(Direction.EAST)

    assert second_result == MoveResult.INVALID
    assert state.get_player(player0).get_agent().get_position() == GridPosition(2, 1)


def test_reset_for_new_turn_allows_another_successful_move():
    state = two_player_state(
        8, 8, GridPosition(1, 1), [GridPosition(1, 1)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )
    api = _new_api(state)
    api.reset_for_new_turn()
    api.move(Direction.EAST)

    api.reset_for_new_turn()
    result = api.move(Direction.EAST)

    assert result == MoveResult.MOVED
    assert state.get_player(player0).get_agent().get_position() == GridPosition(3, 1)


def test_invalid_move_does_not_consume_the_one_move_per_turn_allowance():
    state = two_player_state(
        8, 8, GridPosition(0, 0), [GridPosition(0, 0)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )
    api = _new_api(state)
    api.reset_for_new_turn()

    first_result = api.move(Direction.NORTH)  # out of bounds
    second_result = api.move(Direction.EAST)  # now a real move

    assert first_result == MoveResult.INVALID
    assert second_result == MoveResult.MOVED
