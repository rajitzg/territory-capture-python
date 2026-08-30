"""Owns the complete death/reset operation for a player: clearing their
trail and territory, restoring starting territory, and repositioning
their agent."""

from territorygame.api.grid_position import GridPosition
from territorygame.domain.game_state import GameState
from territorygame.domain.player_id import PlayerId
from territorygame.helpers.movement_utils import manhattan_distance


class RespawnService:
    def respawn(self, state: GameState, player_id: PlayerId) -> None:
        board = state.get_board()
        player = state.get_player(player_id)
        agent = player.get_agent()

        for trail_cell in agent.get_active_trail():
            board.set_trail_owner(trail_cell, None)
        agent.clear_trail()

        board.clear_all_territory_of(player_id)
        for cell in player.get_starting_territory():
            board.set_territory_owner(cell, player_id)

        agent.set_position(self._choose_position(state, player_id))

    def _choose_position(self, state: GameState, player_id: PlayerId) -> GridPosition:
        player = state.get_player(player_id)
        respawn_position = player.get_agent().get_respawn_position()
        opponent_position = state.get_opponent(player_id).get_agent().get_position()

        if respawn_position != opponent_position:
            return respawn_position

        within_starting_territory = [
            cell for cell in player.get_starting_territory() if cell != opponent_position
        ]
        if within_starting_territory:
            return min(within_starting_territory, key=self._nearest_to_respawn_key(respawn_position))

        # Starting territory is fully blocked (e.g. a 1-cell starting territory
        # with the opponent standing on it): fall back to the nearest free cell
        # anywhere on the board rather than failing.
        board = state.get_board()
        candidates = [
            cell for cell in self._all_positions(board.get_width(), board.get_height())
            if cell != opponent_position
        ]
        if not candidates:
            raise RuntimeError(f"No unoccupied cell available anywhere on the board for {player_id}")
        return min(candidates, key=self._nearest_to_respawn_key(respawn_position))

    @staticmethod
    def _nearest_to_respawn_key(respawn_position: GridPosition):
        def key(cell: GridPosition) -> tuple[int, int, int]:
            return (manhattan_distance(cell, respawn_position), cell.y, cell.x)
        return key

    @staticmethod
    def _all_positions(width: int, height: int) -> list[GridPosition]:
        return [GridPosition(x, y) for y in range(height) for x in range(width)]
