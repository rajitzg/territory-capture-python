"""Resolves the rules of a single requested move: bounds and occupancy
validation, trail collision (self-death, opponent-kill), trail extension,
and trail closure/capture. Resolution order is deterministic and mirrors
the spec's rules section exactly."""

from territorygame.api.direction import Direction
from territorygame.api.move_result import MoveResult
from territorygame.domain.game_state import GameState
from territorygame.domain.player_id import PlayerId
from territorygame.helpers.movement_utils import next_position
from territorygame.rules.respawn_service import RespawnService
from territorygame.rules.territory_resolver import TerritoryResolver


class MoveResolver:
    def __init__(self, respawn_service: RespawnService, territory_resolver: TerritoryResolver) -> None:
        self._respawn_service = respawn_service
        self._territory_resolver = territory_resolver

    def resolve(self, state: GameState, mover_id: PlayerId, direction: Direction) -> MoveResult:
        board = state.get_board()
        mover = state.get_player(mover_id)
        opponent = state.get_opponent(mover_id)
        mover_agent = mover.get_agent()

        destination = next_position(mover_agent.get_position(), direction)
        if not board.is_within_bounds(destination):
            return MoveResult.INVALID
        if destination == opponent.get_agent().get_position():
            return MoveResult.INVALID

        trail_owner_at_destination = board.trail_owner_at(destination)
        if mover_id == trail_owner_at_destination:
            self._respawn_service.respawn(state, mover_id)
            state.increment_death_count(mover_id)
            state.decrement_remaining_turns(mover_id)
            return MoveResult.DIED

        # Move the mover onto its destination before respawning a killed
        # opponent, so RespawnService's occupancy check sees where the mover
        # actually ends up rather than where it moved from. Otherwise, if the
        # mover is stepping onto the opponent's own respawn point, the
        # opponent could respawn there and the mover would then move onto
        # the same cell.
        mover_agent.set_position(destination)

        if opponent.get_id() == trail_owner_at_destination:
            self._respawn_service.respawn(state, opponent.get_id())
            state.increment_kill_count(mover_id)
            state.increment_death_count(opponent.get_id())

        territory_owner_at_destination = board.territory_owner_at(destination)
        if mover_id == territory_owner_at_destination and not mover_agent.is_trail_empty():
            self._territory_resolver.apply_capture(state, mover_id)
            state.decrement_remaining_turns(mover_id)
            return MoveResult.CAPTURED

        if mover_id != territory_owner_at_destination:
            board.set_trail_owner(destination, mover_id)
            mover_agent.append_trail(destination)
        state.decrement_remaining_turns(mover_id)
        return MoveResult.MOVED
