"""Player-scoped facade over authoritative state and the move operation.
One instance is created per player and reused for the whole match; it
never exposes backend domain objects, and every returned collection is a
defensive copy so candidate code cannot mutate authoritative state."""

from territorygame.api.direction import Direction
from territorygame.api.game_api import GameApi
from territorygame.api.grid_position import GridPosition
from territorygame.api.move_result import MoveResult
from territorygame.api.visible_cell import VisibleCell
from territorygame.domain.game_state import GameState
from territorygame.domain.player_id import PlayerId
from territorygame.rules.move_resolver import MoveResolver
from territorygame.visibility.visibility_service import VisibilityService


class GameApiImpl(GameApi):
    def __init__(
        self, state: GameState, owner: PlayerId, move_resolver: MoveResolver, visibility_service: VisibilityService
    ) -> None:
        self._state = state
        self._owner = owner
        self._move_resolver = move_resolver
        self._visibility_service = visibility_service
        self._has_moved_this_turn = False
        self._last_result_this_turn: MoveResult | None = None

    def get_agent_position(self) -> GridPosition:
        return self._state.get_player(self._owner).get_agent().get_position()

    def get_respawn_position(self) -> GridPosition:
        return self._state.get_player(self._owner).get_agent().get_respawn_position()

    def get_owned_territory_cell_count(self) -> int:
        return self._state.get_board().territory_count(self._owner)

    def get_opponent_territory_cell_count(self) -> int:
        return self._state.get_board().territory_count(self._state.get_opponent(self._owner).get_id())

    def get_remaining_turns(self) -> int:
        return self._state.get_remaining_turns(self._owner)

    def get_active_trail(self) -> list[GridPosition]:
        return self._state.get_player(self._owner).get_agent().get_active_trail()

    def get_visible_grid(self) -> tuple[tuple[VisibleCell, ...], ...]:
        return self._visibility_service.compute_visible_grid(self._state, self._owner)

    def get_board_width(self) -> int:
        return self._state.get_board().get_width()

    def get_board_height(self) -> int:
        return self._state.get_board().get_height()

    def move(self, direction: Direction) -> MoveResult:
        if self._has_moved_this_turn:
            return MoveResult.INVALID
        result = self._move_resolver.resolve(self._state, self._owner, direction)
        if result != MoveResult.INVALID:
            self._has_moved_this_turn = True
            self._last_result_this_turn = result
        return result

    def reset_for_new_turn(self) -> None:
        """Clears the one-successful-move-per-turn guard. Called before each
        turn. Internal to the engine module — used only by TurnManager, the
        Python equivalent of Java's package-private access."""
        self._has_moved_this_turn = False
        self._last_result_this_turn = None

    def was_move_made_this_turn(self) -> bool:
        return self._has_moved_this_turn

    def get_last_result_this_turn(self) -> MoveResult | None:
        return self._last_result_this_turn
