from territorygame.api.grid_position import GridPosition
from territorygame.domain.player_id import PlayerId
from territorygame.rules.respawn_service import RespawnService
from tests.territorygame.test_games import two_player_state

player0 = PlayerId(0)
player1 = PlayerId(1)
respawn_service = RespawnService()

RESPAWN = GridPosition(5, 5)
STARTING_TERRITORY = [
    GridPosition(4, 4), GridPosition(5, 4), GridPosition(6, 4),
    GridPosition(4, 5), GridPosition(5, 5), GridPosition(6, 5),
    GridPosition(4, 6), GridPosition(5, 6), GridPosition(6, 6),
]


def _build_state(opponent_position):
    return two_player_state(20, 20, RESPAWN, STARTING_TERRITORY, opponent_position, [opponent_position], 10)


def test_death_clears_territory_captured_beyond_starting_territory():
    state = _build_state(GridPosition(15, 15))
    captured_elsewhere = GridPosition(0, 0)
    state.get_board().set_territory_owner(captured_elsewhere, player0)

    respawn_service.respawn(state, player0)

    assert state.get_board().territory_owner_at(captured_elsewhere) is None


def test_death_restores_exactly_the_starting_territory():
    state = _build_state(GridPosition(15, 15))

    respawn_service.respawn(state, player0)

    for cell in STARTING_TERRITORY:
        assert state.get_board().territory_owner_at(cell) == player0
    assert state.get_board().territory_count(player0) == len(STARTING_TERRITORY)


def test_respawn_places_agent_at_configured_position_when_free():
    state = _build_state(GridPosition(15, 15))

    respawn_service.respawn(state, player0)

    assert state.get_player(player0).get_agent().get_position() == RESPAWN


def test_respawn_falls_back_to_nearest_unoccupied_starting_cell_when_respawn_position_is_occupied():
    state = _build_state(RESPAWN)

    respawn_service.respawn(state, player0)

    # Four cells are at Manhattan distance 1 from (5,5): (5,4),(4,5),(6,5),(5,6).
    # Lowest y first breaks the tie: (5,4).
    assert state.get_player(player0).get_agent().get_position() == GridPosition(5, 4)


def test_active_trail_is_cleared_on_death():
    state = _build_state(GridPosition(15, 15))
    trail_cell = GridPosition(10, 10)
    state.get_board().set_trail_owner(trail_cell, player0)
    state.get_player(player0).get_agent().append_trail(trail_cell)

    respawn_service.respawn(state, player0)

    assert state.get_player(player0).get_agent().is_trail_empty()
    assert state.get_board().trail_owner_at(trail_cell) is None


def test_respawn_falls_back_to_the_whole_board_when_starting_territory_is_fully_blocked():
    single_cell_respawn = GridPosition(5, 5)
    state = two_player_state(
        20, 20, single_cell_respawn, [single_cell_respawn], single_cell_respawn, [single_cell_respawn], 10
    )

    respawn_service.respawn(state, player0)

    assert state.get_player(player0).get_agent().get_position() == GridPosition(5, 4)


def test_respawning_one_player_does_not_affect_the_other():
    state = _build_state(GridPosition(15, 15))

    respawn_service.respawn(state, player0)

    assert state.get_player(player1).get_agent().get_position() == GridPosition(15, 15)
    assert state.get_board().territory_count(player1) == 1
