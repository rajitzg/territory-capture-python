"""Immutable, fully copied view of match state for observers (the GUI).
Contains no behavior beyond display-derived values, and is safe to share
across threads.

error_message is non-None exactly when the most recent turn (or the engine
itself) failed in some way worth surfacing to the user; it is display-only
and never affects match state."""

from dataclasses import dataclass

from territorygame.api.grid_position import GridPosition
from territorygame.api.move_result import MoveResult
from territorygame.domain.player_id import PlayerId

_KILL_SCORE_BONUS = 10


@dataclass(frozen=True)
class CellSnapshot:
    """Territory/trail ownership of one cell; either owner may be None."""

    territory_owner: PlayerId | None
    trail_owner: PlayerId | None


@dataclass(frozen=True)
class PlayerSnapshot:
    """One player's displayable state at the moment of the snapshot."""

    id: PlayerId
    position: GridPosition
    territory_count: int
    kill_count: int
    death_count: int
    remaining_turns: int
    trail: tuple[GridPosition, ...]
    debug_state: str | None

    def score(self) -> int:
        """Display-only composite score; the win condition still uses territory_count alone."""
        return self.territory_count + self.kill_count * _KILL_SCORE_BONUS


@dataclass(frozen=True)
class GameSnapshot:
    width: int
    height: int
    cells: tuple[tuple[CellSnapshot, ...], ...]
    players: tuple[PlayerSnapshot, ...]
    active_player_id: PlayerId
    last_move_result: MoveResult | None
    visibility_window_size: int
    game_over: bool
    error_message: str | None
