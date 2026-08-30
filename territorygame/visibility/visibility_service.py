"""Produces candidate-facing observations from authoritative state, owning
the translation from internal player identities to relative SELF/OPPONENT
occupant and territory views."""

from territorygame.api.grid_position import GridPosition
from territorygame.api.occupant_view import OccupantView
from territorygame.api.territory_view import TerritoryView
from territorygame.api.visible_cell import VisibleCell
from territorygame.domain.agent import Agent
from territorygame.domain.board import Board
from territorygame.domain.game_state import GameState
from territorygame.domain.player_id import PlayerId


class VisibilityService:
    def __init__(self, window_size: int) -> None:
        self._window_size = window_size

    def compute_visible_grid(
        self, state: GameState, viewer_id: PlayerId
    ) -> tuple[tuple[VisibleCell, ...], ...]:
        """Returns a window of cells centered on viewer_id's agent, clipped
        to the board, indexed [row][column] (y, then x)."""
        board = state.get_board()
        viewer = state.get_player(viewer_id)
        opponent = state.get_opponent(viewer_id)
        center = viewer.get_agent().get_position()

        half = self._window_size // 2
        min_x = max(0, center.x - half)
        max_x = min(board.get_width() - 1, center.x + half)
        min_y = max(0, center.y - half)
        max_y = min(board.get_height() - 1, center.y + half)

        rows = []
        for y in range(min_y, max_y + 1):
            row = []
            for x in range(min_x, max_x + 1):
                position = GridPosition(x, y)
                row.append(
                    VisibleCell(
                        position,
                        self._classify_occupant(
                            board, position, viewer.get_agent(), opponent.get_agent(), viewer_id, opponent.get_id()
                        ),
                        self._classify_territory(board, position, viewer_id, opponent.get_id()),
                    )
                )
            rows.append(tuple(row))
        return tuple(rows)

    @staticmethod
    def _classify_occupant(
        board: Board,
        position: GridPosition,
        viewer_agent: Agent,
        opponent_agent: Agent,
        viewer_id: PlayerId,
        opponent_id: PlayerId,
    ) -> OccupantView:
        if position == viewer_agent.get_position():
            return OccupantView.SELF_AGENT
        if position == opponent_agent.get_position():
            return OccupantView.OPPONENT_AGENT
        trail_owner = board.trail_owner_at(position)
        if viewer_id == trail_owner:
            return OccupantView.SELF_TRAIL
        if opponent_id == trail_owner:
            return OccupantView.OPPONENT_TRAIL
        return OccupantView.EMPTY

    @staticmethod
    def _classify_territory(
        board: Board, position: GridPosition, viewer_id: PlayerId, opponent_id: PlayerId
    ) -> TerritoryView:
        territory_owner = board.territory_owner_at(position)
        if viewer_id == territory_owner:
            return TerritoryView.SELF
        if opponent_id == territory_owner:
            return TerritoryView.OPPONENT
        return TerritoryView.UNOWNED
