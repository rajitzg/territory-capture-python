from territorygame.api.direction import Direction
from territorygame.api.grid_position import GridPosition
from territorygame.api.move_result import MoveResult
from territorygame.domain.player_id import PlayerId
from territorygame.rules.move_resolver import MoveResolver
from territorygame.rules.respawn_service import RespawnService
from territorygame.rules.territory_resolver import TerritoryResolver
from tests.territorygame.test_games import two_player_state

player0 = PlayerId(0)
player1 = PlayerId(1)
resolver = MoveResolver(RespawnService(), TerritoryResolver())


def test_valid_move_outside_territory_starts_a_trail_and_consumes_a_turn():
    state = two_player_state(
        8, 8, GridPosition(1, 1), [GridPosition(1, 1)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )

    result = resolver.resolve(state, player0, Direction.EAST)

    assert result == MoveResult.MOVED
    assert state.get_player(player0).get_agent().get_position() == GridPosition(2, 1)
    assert state.get_player(player0).get_agent().get_active_trail() == [GridPosition(2, 1)]
    assert state.get_remaining_turns(player0) == 9


def test_move_off_the_board_is_invalid():
    state = two_player_state(
        8, 8, GridPosition(0, 0), [GridPosition(0, 0)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )

    result = resolver.resolve(state, player0, Direction.NORTH)

    assert result == MoveResult.INVALID


def test_move_onto_opponent_agent_is_invalid():
    state = two_player_state(
        8, 8, GridPosition(1, 1), [GridPosition(1, 1)], GridPosition(2, 1), [GridPosition(2, 1)], 10
    )

    result = resolver.resolve(state, player0, Direction.EAST)

    assert result == MoveResult.INVALID


def test_invalid_move_leaves_position_and_trail_unchanged():
    state = two_player_state(
        8, 8, GridPosition(0, 0), [GridPosition(0, 0)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )

    resolver.resolve(state, player0, Direction.NORTH)

    assert state.get_player(player0).get_agent().get_position() == GridPosition(0, 0)
    assert state.get_player(player0).get_agent().is_trail_empty()


def test_invalid_move_does_not_decrement_turns():
    state = two_player_state(
        8, 8, GridPosition(0, 0), [GridPosition(0, 0)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )

    resolver.resolve(state, player0, Direction.NORTH)

    assert state.get_remaining_turns(player0) == 10


def test_second_move_outside_territory_extends_the_trail():
    state = two_player_state(
        8, 8, GridPosition(1, 1), [GridPosition(1, 1)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )

    resolver.resolve(state, player0, Direction.EAST)
    resolver.resolve(state, player0, Direction.EAST)

    assert state.get_player(player0).get_agent().get_active_trail() == [
        GridPosition(2, 1), GridPosition(3, 1)
    ]


def test_moving_within_own_territory_with_no_active_trail_is_just_a_move():
    state = two_player_state(
        8, 8, GridPosition(1, 1), [GridPosition(1, 1), GridPosition(2, 1)],
        GridPosition(6, 6), [GridPosition(6, 6)], 10
    )

    result = resolver.resolve(state, player0, Direction.EAST)

    assert result == MoveResult.MOVED
    assert state.get_player(player0).get_agent().is_trail_empty()


def test_returning_to_own_territory_with_a_non_empty_trail_closes():
    state = two_player_state(
        8, 8, GridPosition(2, 2), [GridPosition(2, 2)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )

    resolver.resolve(state, player0, Direction.EAST)  # -> (3,2), trail=[(3,2)]
    result = resolver.resolve(state, player0, Direction.WEST)  # back to (2,2)

    assert result == MoveResult.CAPTURED
    assert state.get_player(player0).get_agent().is_trail_empty()


def test_moving_onto_own_active_trail_kills_the_mover():
    state = two_player_state(
        8, 8, GridPosition(2, 2), [GridPosition(2, 2)], GridPosition(7, 7), [GridPosition(7, 7)], 10
    )

    resolver.resolve(state, player0, Direction.EAST)   # (3,2) trail
    resolver.resolve(state, player0, Direction.EAST)   # (4,2) trail
    resolver.resolve(state, player0, Direction.SOUTH)  # (4,3) trail
    resolver.resolve(state, player0, Direction.WEST)   # (3,3) trail
    result = resolver.resolve(state, player0, Direction.NORTH)  # -> (3,2), own trail

    assert result == MoveResult.DIED
    assert state.get_player(player0).get_agent().get_position() == GridPosition(2, 2)
    assert state.get_player(player0).get_agent().is_trail_empty()
    assert state.get_board().territory_count(player0) == 1


def test_crossing_opponent_trail_kills_them_and_mover_survives_and_continues():
    state = two_player_state(
        8, 8, GridPosition(7, 7), [GridPosition(7, 7)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )

    resolver.resolve(state, player1, Direction.EAST)   # (6,6)->(7,6) trail
    resolver.resolve(state, player1, Direction.NORTH)  # (7,6)->(7,5) trail

    result = resolver.resolve(state, player0, Direction.NORTH)  # (7,7)->(7,6)

    assert result == MoveResult.MOVED
    assert state.get_player(player0).get_agent().get_position() == GridPosition(7, 6)
    assert state.get_player(player1).get_agent().get_position() == GridPosition(6, 6)
    assert state.get_player(player1).get_agent().is_trail_empty()
    assert state.get_board().trail_owner_at(GridPosition(7, 6)) == player0


def test_crossing_opponent_trail_increments_the_mover_kill_count():
    state = two_player_state(
        8, 8, GridPosition(7, 7), [GridPosition(7, 7)], GridPosition(6, 6), [GridPosition(6, 6)], 10
    )
    resolver.resolve(state, player1, Direction.EAST)
    resolver.resolve(state, player1, Direction.NORTH)

    resolver.resolve(state, player0, Direction.NORTH)

    assert state.get_kill_count(player0) == 1
    assert state.get_kill_count(player1) == 0


def test_moving_onto_opponents_trail_at_its_own_respawn_point_does_not_stack_agents():
    # Regression test for the bug where killing an opponent by stepping onto
    # a trail cell that happens to sit on the opponent's own respawn point
    # could respawn the opponent onto the mover's destination, stacking both
    # agents on one cell.
    opponent_respawn = GridPosition(5, 5)
    opponent_starting_territory = [
        GridPosition(4, 4), GridPosition(5, 4), GridPosition(6, 4),
        GridPosition(4, 5), GridPosition(5, 5), GridPosition(6, 5),
        GridPosition(4, 6), GridPosition(5, 6), GridPosition(6, 6),
    ]
    state = two_player_state(
        10, 10, GridPosition(4, 8), [GridPosition(4, 8)], opponent_respawn, opponent_starting_territory, 10
    )
    state.get_player(player1).get_agent().set_position(GridPosition(9, 9))
    state.get_board().set_trail_owner(opponent_respawn, player1)
    state.get_player(player1).get_agent().append_trail(opponent_respawn)
    state.get_player(player0).get_agent().set_position(GridPosition(4, 5))

    result = resolver.resolve(state, player0, Direction.EAST)  # (4,5) -> (5,5)

    assert result == MoveResult.MOVED
    mover_position = state.get_player(player0).get_agent().get_position()
    opponent_new_position = state.get_player(player1).get_agent().get_position()
    assert mover_position == opponent_respawn
    assert mover_position != opponent_new_position
    assert state.get_kill_count(player0) == 1


def test_closing_a_loop_on_a_cell_that_kills_the_opponent_preserves_their_starting_territory():
    # Player0 returns home (closing a loop) onto a cell that also has
    # player1's trail, so both a capture and a kill resolve in one move.
    # Respawn then restores the start platform.
    p1_start = GridPosition(4, 4)
    p0_territory = [
        GridPosition(1, 1),
        GridPosition(3, 3), GridPosition(4, 3), GridPosition(5, 3),
        GridPosition(3, 4), GridPosition(5, 4),
        GridPosition(3, 5), GridPosition(4, 5), GridPosition(5, 5),
    ]
    state = two_player_state(8, 8, GridPosition(1, 1), p0_territory, p1_start, [p1_start], 10)

    state.get_player(player0).get_agent().set_position(GridPosition(1, 2))
    state.get_board().set_trail_owner(GridPosition(1, 2), player0)
    state.get_player(player0).get_agent().append_trail(GridPosition(1, 2))

    state.get_player(player1).get_agent().set_position(GridPosition(1, 3))
    state.get_board().set_trail_owner(GridPosition(1, 1), player1)
    state.get_player(player1).get_agent().append_trail(GridPosition(1, 1))

    result = resolver.resolve(state, player0, Direction.NORTH)

    assert result == MoveResult.CAPTURED
    assert state.get_kill_count(player0) == 1
    assert state.get_player(player1).get_agent().get_position() == p1_start
    assert state.get_board().territory_owner_at(p1_start) == player1
    assert state.get_board().territory_count(player1) == 1


def test_enclosing_opponent_start_without_a_kill_claims_it_and_does_not_respawn_them():
    p1_start = GridPosition(3, 3)
    p1_position = GridPosition(7, 7)
    state = two_player_state(8, 8, GridPosition(2, 2), [GridPosition(2, 2)], p1_start, [p1_start], 10)
    state.get_player(player1).get_agent().set_position(p1_position)

    perimeter = [
        GridPosition(3, 2), GridPosition(4, 2),
        GridPosition(4, 3), GridPosition(4, 4),
        GridPosition(3, 4), GridPosition(2, 4), GridPosition(2, 3),
    ]
    for cell in perimeter:
        state.get_board().set_trail_owner(cell, player0)
        state.get_player(player0).get_agent().append_trail(cell)
    state.get_player(player0).get_agent().set_position(GridPosition(2, 3))

    result = resolver.resolve(state, player0, Direction.NORTH)

    assert result == MoveResult.CAPTURED
    assert state.get_kill_count(player0) == 0
    assert state.get_death_count(player1) == 0
    assert state.get_player(player1).get_agent().get_position() == p1_position
    assert state.get_board().territory_owner_at(p1_start) == player0
    assert state.get_board().territory_count(player1) == 0
