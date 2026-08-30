from territorygame.api.grid_position import GridPosition
from territorygame.domain.player_id import PlayerId
from territorygame.rules.territory_resolver import TerritoryResolver
from tests.territorygame.test_games import two_player_state

capturer = PlayerId(0)
opponent = PlayerId(1)
resolver = TerritoryResolver()

PERIMETER = [
    GridPosition(3, 2), GridPosition(4, 2), GridPosition(4, 3), GridPosition(4, 4),
    GridPosition(3, 4), GridPosition(2, 4), GridPosition(2, 3),
]
HOME = GridPosition(2, 2)
ENCLOSED = GridPosition(3, 3)


def _build_state_with_pending_trail():
    state = two_player_state(8, 8, HOME, [HOME], GridPosition(7, 7), [GridPosition(7, 7)], 10)
    for cell in PERIMETER:
        state.get_board().set_trail_owner(cell, capturer)
        state.get_player(capturer).get_agent().append_trail(cell)
    return state


def test_simple_rectangular_capture_claims_trail_and_enclosed_cells():
    state = _build_state_with_pending_trail()

    resolver.apply_capture(state, capturer)

    for cell in PERIMETER:
        assert state.get_board().territory_owner_at(cell) == capturer
    assert state.get_board().territory_owner_at(ENCLOSED) == capturer
    assert state.get_board().territory_count(capturer) == 9  # home + 7 perimeter + 1 enclosed


def test_capture_flips_opponent_territory_inside_the_enclosed_region():
    state = _build_state_with_pending_trail()
    state.get_board().set_territory_owner(ENCLOSED, opponent)

    resolver.apply_capture(state, capturer)

    assert state.get_board().territory_owner_at(ENCLOSED) == capturer
    assert state.get_board().territory_count(opponent) == 1


def test_unrelated_opponent_trail_inside_the_enclosed_region_is_untouched():
    state = _build_state_with_pending_trail()
    state.get_board().set_trail_owner(ENCLOSED, opponent)

    resolver.apply_capture(state, capturer)

    assert state.get_board().territory_owner_at(ENCLOSED) == capturer
    assert state.get_board().trail_owner_at(ENCLOSED) == opponent


def test_capture_clears_the_capturers_active_trail():
    state = _build_state_with_pending_trail()

    resolver.apply_capture(state, capturer)

    assert state.get_player(capturer).get_agent().is_trail_empty()
    for cell in PERIMETER:
        assert state.get_board().trail_owner_at(cell) is None


def test_cells_outside_the_loop_are_not_captured():
    state = _build_state_with_pending_trail()
    far_away = GridPosition(0, 0)

    resolver.apply_capture(state, capturer)

    assert state.get_board().territory_owner_at(far_away) is None
