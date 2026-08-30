from territorygame.api.grid_position import GridPosition
from territorygame.api.occupant_view import OccupantView
from territorygame.api.territory_view import TerritoryView
from territorygame.domain.player_id import PlayerId
from territorygame.visibility.visibility_service import VisibilityService
from tests.territorygame.test_games import two_player_state

player0 = PlayerId(0)
player1 = PlayerId(1)


def _cell_at(grid, position):
    for row in grid:
        for cell in row:
            if cell.position == position:
                return cell
    raise AssertionError(f"Position not in visible grid: {position}")


def test_window_is_full_size_when_far_from_every_edge():
    state = two_player_state(
        20, 20, GridPosition(10, 10), [GridPosition(10, 10)], GridPosition(19, 19), [GridPosition(19, 19)], 10
    )
    service = VisibilityService(5)  # half=2

    grid = service.compute_visible_grid(state, player0)

    assert len(grid) == 5
    assert len(grid[0]) == 5
    assert grid[2][2].position == GridPosition(10, 10)


def test_window_clips_at_the_board_corner():
    state = two_player_state(
        20, 20, GridPosition(0, 0), [GridPosition(0, 0)], GridPosition(19, 19), [GridPosition(19, 19)], 10
    )
    service = VisibilityService(5)  # half=2

    grid = service.compute_visible_grid(state, player0)

    # Window would be x:[-2,2], y:[-2,2]; clipped to x:[0,2], y:[0,2] -> 3x3.
    assert len(grid) == 3
    assert len(grid[0]) == 3
    assert grid[0][0].position == GridPosition(0, 0)


def test_ownership_translates_to_self_and_opponent_relative_to_viewer():
    player0_territory = GridPosition(4, 5)
    player1_territory = GridPosition(7, 6)
    state = two_player_state(
        10, 10,
        GridPosition(5, 5), [GridPosition(5, 5), player0_territory],
        GridPosition(6, 6), [GridPosition(6, 6), player1_territory],
        10,
    )
    service = VisibilityService(9)

    from_player0 = service.compute_visible_grid(state, player0)
    from_player1 = service.compute_visible_grid(state, player1)

    assert _cell_at(from_player0, player0_territory).occupant == OccupantView.EMPTY
    assert _cell_at(from_player0, player0_territory).territory == TerritoryView.SELF
    assert _cell_at(from_player0, player1_territory).occupant == OccupantView.EMPTY
    assert _cell_at(from_player0, player1_territory).territory == TerritoryView.OPPONENT
    assert _cell_at(from_player1, player0_territory).occupant == OccupantView.EMPTY
    assert _cell_at(from_player1, player0_territory).territory == TerritoryView.OPPONENT
    assert _cell_at(from_player1, player1_territory).occupant == OccupantView.EMPTY
    assert _cell_at(from_player1, player1_territory).territory == TerritoryView.SELF


def test_agent_positions_are_reported_as_self_or_opponent_agent():
    state = two_player_state(
        10, 10, GridPosition(5, 5), [GridPosition(5, 5)], GridPosition(6, 5), [GridPosition(6, 5)], 10
    )
    service = VisibilityService(9)

    grid = service.compute_visible_grid(state, player0)

    assert _cell_at(grid, GridPosition(5, 5)).occupant == OccupantView.SELF_AGENT
    assert _cell_at(grid, GridPosition(6, 5)).occupant == OccupantView.OPPONENT_AGENT


def test_trail_occupant_does_not_hide_territory():
    state = two_player_state(10, 10, GridPosition(5, 5), [GridPosition(5, 5)], GridPosition(0, 0), [], 10)
    trail_over_territory = GridPosition(4, 5)
    state.get_board().set_territory_owner(trail_over_territory, player0)
    state.get_board().set_trail_owner(trail_over_territory, player0)

    service = VisibilityService(9)
    cell = _cell_at(service.compute_visible_grid(state, player0), trail_over_territory)

    assert cell.occupant == OccupantView.SELF_TRAIL
    assert cell.territory == TerritoryView.SELF


def test_opponent_trail_on_viewer_land_reports_both_layers():
    state = two_player_state(10, 10, GridPosition(5, 5), [GridPosition(5, 5)], GridPosition(0, 0), [], 10)
    cut = GridPosition(4, 5)
    state.get_board().set_territory_owner(cut, player0)
    state.get_board().set_trail_owner(cut, player1)

    service = VisibilityService(9)
    cell = _cell_at(service.compute_visible_grid(state, player0), cut)

    assert cell.occupant == OccupantView.OPPONENT_TRAIL
    assert cell.territory == TerritoryView.SELF


def test_unoccupied_unowned_cell_is_empty_and_unowned():
    state = two_player_state(
        10, 10, GridPosition(5, 5), [GridPosition(5, 5)], GridPosition(0, 0), [GridPosition(0, 0)], 10
    )
    service = VisibilityService(9)
    cell = _cell_at(service.compute_visible_grid(state, player0), GridPosition(6, 5))

    assert cell.occupant == OccupantView.EMPTY
    assert cell.territory == TerritoryView.UNOWNED
