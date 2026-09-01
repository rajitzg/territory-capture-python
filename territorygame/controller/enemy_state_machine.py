"""Framework code: the standard opponent used for assessment runs. Not part
of the candidate-facing surface.

Grows territory in small rectangular bites that always stay inside a
configurable box around its own head — so by construction it can never be
caught out in the open with no safe way home — and only fights when the
opponent trespasses onto its own land."""

import random
from enum import Enum, auto

from territorygame.api.agent_controller import AgentController
from territorygame.api.direction import Direction
from territorygame.api.game_api import GameApi
from territorygame.api.grid_position import GridPosition
from territorygame.api.occupant_view import OccupantView
from territorygame.api.territory_view import TerritoryView
from territorygame.helpers.movement_utils import (
    find_cell,
    is_valid_board_move,
    is_within_board,
    manhattan_distance,
    next_position,
    valid_directions,
)

_SAFETY_GRID_SIZE = 7
_OUT_LOOKAHEAD = 2


class _Phase(Enum):
    ATTACK = auto()
    REPOSITION = auto()
    OUT = auto()
    ACROSS = auto()
    BACK = auto()


class EnemyStateMachine(AgentController):
    def __init__(self) -> None:
        self._phase = _Phase.OUT
        self._out_direction: Direction | None = None
        self._steps_out = 0
        self._across_direction: Direction | None = None
        self._reposition_direction: Direction | None = None
        self._random = random.Random(42)

    def take_turn(self, game: GameApi) -> None:
        intrusion = self._find_opponent_trail_on_our_territory(game)
        if intrusion is not None:
            self._phase = _Phase.ATTACK
            direction = self._pick_attack(game, intrusion)
        elif not game.get_active_trail():
            direction = self._pick_trail_free(game)
        else:
            direction = self._pick_expedition(game)
        game.move(direction)

    def get_debug_state(self) -> str | None:
        return self._phase.name

    # ---- ATTACK / REPOSITION ---------------------------------------------

    def _pick_attack(self, game: GameApi, target: GridPosition) -> Direction:
        """A free kill: crossing their trail sends them back to respawn, no risk to us."""
        return self._choose_best(game, self._huntable_directions(game), self._distance_to_key(game, target))

    def _pick_trail_free(self, game: GameApi) -> Direction:
        """Chooses a move on owned territory or starts OUT when the chosen move leaves it."""
        safe = self._safe_directions(game)
        territory_only = [d for d in safe if self._is_self_territory(game, self._destination(game, d))]

        if (
            self._reposition_direction is not None
            and self._reposition_direction in territory_only
            and self._distance_to_outside_territory(game, self._reposition_direction) <= _OUT_LOOKAHEAD
        ):
            self._phase = _Phase.REPOSITION
            return self._reposition_direction

        outside_territory = [d for d in safe if d not in territory_only]
        if outside_territory:
            self._phase = _Phase.OUT
            self._out_direction = (
                self._reposition_direction
                if self._reposition_direction in outside_territory
                else self._choose_random(game, self._prefer_vertical(outside_territory))
            )
            self._reposition_direction = None
            self._steps_out = 1
            return self._out_direction

        self._phase = _Phase.REPOSITION
        approaches = self._closest_approach_directions(game, territory_only)
        if approaches:
            self._reposition_direction = self._choose_random(game, approaches)
            return self._reposition_direction
        if self._reposition_direction is not None and self._reposition_direction in territory_only:
            return self._reposition_direction
        self._reposition_direction = self._choose_random(game, safe if not territory_only else territory_only)
        return self._reposition_direction

    # ---- Expedition: OUT / ACROSS / BACK --------------------------------

    def _pick_expedition(self, game: GameApi) -> Direction:
        """Continues whichever part of an active expedition was last selected."""
        if self._phase == _Phase.OUT:
            return self._pick_out(game)
        if self._phase == _Phase.ACROSS:
            return self._pick_across(game)
        # ATTACK/REPOSITION never reach here; BACK, and any interrupted-then-resumed
        # phase left over from an ATTACK detour, both just keep heading home.
        return self._pick_back(game)

    def _pick_out(self, game: GameApi) -> Direction:
        next_head = self._destination(game, self._out_direction)
        if (
            self._out_direction in self._safe_directions(game)
            and not self._is_self_territory(game, next_head)
            and self.fits_safety_grid(next_head, game.get_active_trail(), _SAFETY_GRID_SIZE)
        ):
            self._steps_out += 1
            return self._out_direction
        self._phase = _Phase.ACROSS
        self._across_direction = self._pick_across_direction(game)
        return self._pick_across(game)

    def _pick_across_direction(self, game: GameApi) -> Direction:
        perpendicular = [
            d for d in self.perpendicular_options(self._out_direction)
            if self._can_take_another_across_step(game, d)
        ]
        if not perpendicular:
            # Both perpendicular options are blocked; this will fail the
            # grid/mirror check below and fall back to BACK.
            return self._out_direction
        return self._choose_random(game, perpendicular)

    def _pick_across(self, game: GameApi) -> Direction:
        if self._can_take_another_across_step(game, self._across_direction):
            return self._across_direction
        self._phase = _Phase.BACK
        return self._pick_back(game)

    def _can_take_another_across_step(self, game: GameApi, direction: Direction) -> bool:
        if direction not in self._safe_directions(game):
            return False
        next_head = self._destination(game, direction)
        if not self.fits_safety_grid(next_head, game.get_active_trail(), _SAFETY_GRID_SIZE):
            return False
        mirrored = self.mirror_back(next_head, self._out_direction, self._steps_out)
        return self._is_self_territory(game, mirrored)

    # ---- Shared BACK logic ------------------------------------------------

    def _pick_back(self, game: GameApi) -> Direction:
        """Walks opposite out_direction. ACROSS already required that this path lands on owned land."""
        reverse = self.opposite(self._out_direction)
        safe = self._safe_directions(game)
        return reverse if reverse in safe else self._choose_random(game, safe)

    # ---- Board reading -----------------------------------------------------

    def _safe_directions(self, game: GameApi) -> list[Direction]:
        result = []
        for direction in Direction:
            if not is_valid_board_move(
                game.get_agent_position(), direction, game.get_board_width(), game.get_board_height()
            ):
                continue
            occupant = self._occupant_at(game, self._destination(game, direction))
            if occupant not in (OccupantView.SELF_TRAIL, OccupantView.OPPONENT_TRAIL, OccupantView.OPPONENT_AGENT):
                result.append(direction)
        return result

    def _huntable_directions(self, game: GameApi) -> list[Direction]:
        """Like _safe_directions, but allows stepping onto the opponent's
        trail — that's how a chase ends in a kill."""
        result = []
        for direction in Direction:
            if not is_valid_board_move(
                game.get_agent_position(), direction, game.get_board_width(), game.get_board_height()
            ):
                continue
            occupant = self._occupant_at(game, self._destination(game, direction))
            if occupant not in (OccupantView.SELF_TRAIL, OccupantView.OPPONENT_AGENT):
                result.append(direction)
        return result

    @staticmethod
    def _occupant_at(game: GameApi, position: GridPosition) -> OccupantView:
        cell = find_cell(game.get_visible_grid(), position)
        return OccupantView.EMPTY if cell is None else cell.occupant

    @staticmethod
    def _destination(game: GameApi, direction: Direction) -> GridPosition:
        return next_position(game.get_agent_position(), direction)

    def _closest_approach_directions(self, game: GameApi, candidates: list[Direction]) -> list[Direction]:
        closest: list[Direction] = []
        closest_distance = _OUT_LOOKAHEAD + 1
        for direction in candidates:
            distance = self._distance_to_outside_territory(game, direction)
            if distance < closest_distance:
                closest = []
                closest_distance = distance
            if distance == closest_distance and distance <= _OUT_LOOKAHEAD:
                closest.append(direction)
        return self._prefer_vertical(closest)

    @staticmethod
    def _distance_to_outside_territory(game: GameApi, direction: Direction) -> int:
        position = game.get_agent_position()
        for distance in range(1, _OUT_LOOKAHEAD + 1):
            position = next_position(position, direction)
            if not is_within_board(position, game.get_board_width(), game.get_board_height()):
                break
            cell = find_cell(game.get_visible_grid(), position)
            if cell is None:
                break
            if cell.territory != TerritoryView.SELF:
                return distance
        return _OUT_LOOKAHEAD + 1

    @staticmethod
    def _prefer_vertical(candidates: list[Direction]) -> list[Direction]:
        vertical = [d for d in candidates if EnemyStateMachine.is_vertical(d)]
        return vertical if vertical else candidates

    @staticmethod
    def _is_self_territory(game: GameApi, position: GridPosition) -> bool:
        """False for cells outside the visible window."""
        cell = find_cell(game.get_visible_grid(), position)
        return cell is not None and cell.territory == TerritoryView.SELF

    def _choose_best(self, game: GameApi, candidates: list[Direction], ranking) -> Direction:
        if not candidates:
            return self._fallback(game)
        return min(candidates, key=ranking)

    def _choose_random(self, game: GameApi, candidates: list[Direction]) -> Direction:
        if not candidates:
            return self._fallback(game)
        return candidates[self._random.randrange(len(candidates))]

    @staticmethod
    def _distance_to_key(game: GameApi, target: GridPosition):
        return lambda direction: manhattan_distance(EnemyStateMachine._destination(game, direction), target)

    @staticmethod
    def _find_opponent_trail_on_our_territory(game: GameApi) -> GridPosition | None:
        """Nearest visible cell where the opponent's trail is crossing land
        that's ours — an intrusion worth punishing."""
        from_position = game.get_agent_position()
        best: GridPosition | None = None
        best_distance: int | None = None
        for row in game.get_visible_grid():
            for cell in row:
                if cell.territory == TerritoryView.SELF and cell.occupant == OccupantView.OPPONENT_TRAIL:
                    distance = manhattan_distance(from_position, cell.position)
                    if best_distance is None or distance < best_distance:
                        best_distance = distance
                        best = cell.position
        return best

    @staticmethod
    def _fallback(game: GameApi) -> Direction:
        valid = valid_directions(game)
        return valid[0] if valid else Direction.NORTH

    # ---- Pure helpers (no GameApi; unit-testable directly) ---------------

    @staticmethod
    def chebyshev_distance(a: GridPosition, b: GridPosition) -> int:
        return max(abs(a.x - b.x), abs(a.y - b.y))

    @staticmethod
    def fits_safety_grid(head: GridPosition, trail: list[GridPosition], grid_size: int) -> bool:
        """Every cell in trail must stay within grid_size // 2 of head.
        Vacuously true for an empty trail."""
        half = grid_size // 2
        return all(EnemyStateMachine.chebyshev_distance(cell, head) <= half for cell in trail)

    @staticmethod
    def opposite(direction: Direction) -> Direction:
        return {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
        }[direction]

    @staticmethod
    def perpendicular_options(direction: Direction) -> list[Direction]:
        if direction in (Direction.NORTH, Direction.SOUTH):
            return [Direction.EAST, Direction.WEST]
        return [Direction.NORTH, Direction.SOUTH]

    @staticmethod
    def mirror_back(position: GridPosition, out_direction: Direction, steps: int) -> GridPosition:
        """Walks steps cells in the reverse of out_direction from position."""
        result = position
        reverse = EnemyStateMachine.opposite(out_direction)
        for _ in range(steps):
            result = next_position(result, reverse)
        return result

    @staticmethod
    def is_vertical(direction: Direction) -> bool:
        return direction in (Direction.NORTH, Direction.SOUTH)
