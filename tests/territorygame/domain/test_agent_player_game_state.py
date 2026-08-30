from territorygame.api.grid_position import GridPosition
from territorygame.api.move_result import MoveResult
from territorygame.domain.agent import Agent
from territorygame.domain.board import Board
from territorygame.domain.board_cell import BoardCell
from territorygame.domain.game_state import GameState
from territorygame.domain.player import Player
from territorygame.domain.player_id import PlayerId


def test_player_id_is_a_value_type():
    assert PlayerId(0) == PlayerId(0)
    assert PlayerId(0) != PlayerId(1)


def test_board_cell_starts_with_no_owners():
    cell = BoardCell()
    assert cell.get_territory_owner() is None
    assert cell.get_trail_owner() is None


def test_board_cell_owners_are_independent():
    cell = BoardCell()
    p0, p1 = PlayerId(0), PlayerId(1)
    cell.set_territory_owner(p0)
    cell.set_trail_owner(p1)
    assert cell.get_territory_owner() == p0
    assert cell.get_trail_owner() == p1


def test_agent_tracks_position_and_trail():
    respawn = GridPosition(1, 1)
    agent = Agent(respawn, respawn)

    assert agent.get_position() == respawn
    assert agent.get_respawn_position() == respawn
    assert agent.is_trail_empty()

    agent.set_position(GridPosition(2, 1))
    agent.append_trail(GridPosition(2, 1))

    assert agent.get_position() == GridPosition(2, 1)
    assert not agent.is_trail_empty()
    assert agent.get_active_trail() == [GridPosition(2, 1)]

    agent.clear_trail()
    assert agent.is_trail_empty()


def test_agent_get_active_trail_returns_a_defensive_copy():
    agent = Agent(GridPosition(0, 0), GridPosition(0, 0))
    agent.append_trail(GridPosition(1, 0))

    trail = agent.get_active_trail()
    trail.append(GridPosition(2, 0))

    assert agent.get_active_trail() == [GridPosition(1, 0)]


def test_player_exposes_id_agent_and_starting_territory():
    player_id = PlayerId(0)
    agent = Agent(GridPosition(0, 0), GridPosition(0, 0))
    territory = [GridPosition(0, 0), GridPosition(1, 0)]

    player = Player(player_id, agent, territory)

    assert player.get_id() == player_id
    assert player.get_agent() is agent
    assert player.get_starting_territory() == territory


def _two_player_state() -> GameState:
    board = Board(5, 5)
    player0 = Player(PlayerId(0), Agent(GridPosition(0, 0), GridPosition(0, 0)), [GridPosition(0, 0)])
    player1 = Player(PlayerId(1), Agent(GridPosition(4, 4), GridPosition(4, 4)), [GridPosition(4, 4)])
    return GameState(board, [player0, player1], turns_per_player=3)


def test_game_state_starts_with_the_first_player_active_and_full_turns():
    state = _two_player_state()

    assert state.get_active_player_id() == PlayerId(0)
    assert state.get_remaining_turns(PlayerId(0)) == 3
    assert state.get_remaining_turns(PlayerId(1)) == 3
    assert not state.is_game_over()


def test_game_state_get_opponent_returns_the_other_player():
    state = _two_player_state()

    assert state.get_opponent(PlayerId(0)).get_id() == PlayerId(1)
    assert state.get_opponent(PlayerId(1)).get_id() == PlayerId(0)


def test_game_state_is_game_over_once_every_player_is_out_of_turns():
    state = _two_player_state()
    for _ in range(3):
        state.decrement_remaining_turns(PlayerId(0))
    assert not state.is_game_over()
    for _ in range(3):
        state.decrement_remaining_turns(PlayerId(1))
    assert state.is_game_over()


def test_game_state_tracks_kills_deaths_and_last_move_result():
    state = _two_player_state()

    state.increment_kill_count(PlayerId(0))
    state.increment_death_count(PlayerId(1))
    state.set_last_move_result(MoveResult.CAPTURED)
    state.set_last_turn_error("boom")

    assert state.get_kill_count(PlayerId(0)) == 1
    assert state.get_death_count(PlayerId(1)) == 1
    assert state.get_last_move_result() == MoveResult.CAPTURED
    assert state.get_last_turn_error() == "boom"
