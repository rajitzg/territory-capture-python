"""Framework code: the standard opponent used for assessment runs. Not part
of the candidate-facing surface.

Five states, organized by risk posture and picked fresh every turn
(highest priority first):
- DEFENSIVE - our owned territory just shrank since last turn, meaning an
  opponent capture is in progress or just landed. Chase their visible
  trail for a kill if we can see one; otherwise fall back to heading home.
- RECEDING - safe. Our trail is long, we're low enough on turns that
  pushing further risks not making it back, the opponent is visible and
  close while we're exposed, or we're already ahead and the match is
  nearly over. Head for the nearest owned territory, or shuffle around
  inside it if we're already there.
- AGGRESSIVE - risky. The opponent's trail or territory is visible and
  we're not currently in danger; go take it.
- EXPANDING - the default. Deterministically push toward whichever safe
  direction opens onto the most free space.
- WANDERING - a rare, single-turn detour: pick at random among directions
  whose open-space score is merely close to the best. Never fires two
  turns in a row.

Earlier versions of this bot got stuck in short back-and-forth loops
against itself. WANDERING periodically (and briefly) makes the whole
match non-deterministic, which is enough to knock either agent off any
cycle regardless of its length."""

import random
from enum import Enum, auto

from territorygame.api.agent_controller import AgentController
from territorygame.api.direction import Direction
from territorygame.api.game_api import GameApi
from territorygame.api.grid_position import GridPosition
from territorygame.api.occupant_view import OccupantView
from territorygame.api.territory_view import TerritoryView
from territorygame.api.visible_cell import VisibleCell
from territorygame.helpers.movement_utils import (
    find_cell,
    is_valid_board_move,
    is_within_board,
    manhattan_distance,
    next_position,
    random_direction,
)

_MAX_TRAIL_BEFORE_RETURN = 8
_SAFETY_TURN_BUFFER = 4
_CONSOLIDATE_TURNS_THRESHOLD = 30
_WANDER_OPENNESS_TOLERANCE = 1
_RANDOM_WANDER_CHANCE = 0.01


class _State(Enum):
    DEFENSIVE = auto()
    RECEDING = auto()
    AGGRESSIVE = auto()
    EXPANDING = auto()
    WANDERING = auto()


class EnemyStateMachine(AgentController):
    def __init__(self, seed: int | None = None) -> None:
        """Two instances of this same deterministic logic need different
        seeds, or they'll play out identically for long stretches. Passing
        None seeds from OS entropy, same as Java's no-arg constructor."""
        self._random = random.Random(seed)
        self._current_state = _State.EXPANDING
        self._previous_owned_territory_count = 0
        self._first_move = True
        self._direction: Direction | None = None
        self._best_open_neighbor_count = 0

    def take_turn(self, game: GameApi) -> None:
        # Even with different seeds, two fresh instances facing a symmetric
        # starting position can still tie on every heuristic and open in the
        # same relative direction. Forcing a genuinely random opening move
        # breaks that up front.
        if self._first_move:
            self._first_move = False
            self._current_state = _State.WANDERING
            game.move(self._pick_uniformly_random(game))
            return
        previous_state = self._current_state
        self._current_state = self._decide_state(game, previous_state)
        direction = self._choose_direction(game, self._current_state)
        game.move(direction)

    def get_debug_state(self) -> str | None:
        return (
            f"{self._current_state.name} {self._direction}, "
            f"bestOpenNeighborCount: {self._best_open_neighbor_count}"
        )

    # ---- State selection ----------------------------------------------

    def _decide_state(self, game: GameApi, previous_state: _State) -> _State:
        territory_shrank = game.get_owned_territory_cell_count() < self._previous_owned_territory_count
        self._previous_owned_territory_count = game.get_owned_territory_cell_count()
        if territory_shrank:
            return _State.DEFENSIVE
        if self._should_recede(game):
            return _State.RECEDING
        if self._should_be_aggressive(game):
            return _State.AGGRESSIVE
        if previous_state != _State.WANDERING and self._random.random() < _RANDOM_WANDER_CHANCE:
            return _State.WANDERING
        return _State.EXPANDING

    def _should_recede(self, game: GameApi) -> bool:
        trail = game.get_active_trail()
        if trail:
            if len(trail) >= _MAX_TRAIL_BEFORE_RETURN:
                return True
            if game.get_remaining_turns() <= len(trail) + _SAFETY_TURN_BUFFER:
                return True
            if self._opponent_is_threateningly_close(game):
                return True
        return self._is_endgame_with_lead(game)

    def _should_be_aggressive(self, game: GameApi) -> bool:
        return (
            self._nearest_occupant(game, OccupantView.OPPONENT_TRAIL) is not None
            or self._nearest_territory(game, TerritoryView.OPPONENT) is not None
        )

    def _opponent_is_threateningly_close(self, game: GameApi) -> bool:
        threat_distance = len(game.get_visible_grid()) // 2
        position = self._nearest_occupant(game, OccupantView.OPPONENT_AGENT)
        if position is None:
            return False
        return manhattan_distance(game.get_agent_position(), position) <= threat_distance

    def _is_endgame_with_lead(self, game: GameApi) -> bool:
        return (
            game.get_remaining_turns() <= _CONSOLIDATE_TURNS_THRESHOLD
            and game.get_owned_territory_cell_count() > game.get_opponent_territory_cell_count()
        )

    # ---- Direction selection --------------------------------------------

    def _choose_direction(self, game: GameApi, state: _State) -> Direction:
        if state == _State.DEFENSIVE:
            return self._pick_defensive(game)
        if state == _State.RECEDING:
            return self._pick_receding(game)
        if state == _State.AGGRESSIVE:
            return self._pick_aggressive(game)
        if state == _State.EXPANDING:
            return self._pick_expanding(game)
        return self._pick_wandering(game)

    def _pick_defensive(self, game: GameApi) -> Direction:
        """Chases the opponent's visible trail to stop an in-progress
        capture cold; otherwise falls back to heading home."""
        hunted = self._hunt_opponent_trail(game)
        return hunted if hunted is not None else self._pick_receding(game)

    def _pick_expanding(self, game: GameApi) -> Direction:
        """Deterministically pushes toward whichever safe direction opens
        onto the most free space."""
        best = self._choose_best(self._safe_directions(game), self._most_open_first_key(game))
        self._direction = best
        self._best_open_neighbor_count = self._open_neighbor_count(game, best)
        return best

    def _pick_receding(self, game: GameApi) -> Direction:
        """Stays inside our own territory if any safe move lands there
        (zero trail risk); otherwise heads for the nearest of it."""
        within_territory = [
            direction for direction in self._safe_directions(game)
            if self._territory_at(game, self._destination(game, direction)) == TerritoryView.SELF
        ]
        if within_territory:
            return self._choose_best(within_territory, self._most_open_first_key(game))
        target = self._nearest_territory(game, TerritoryView.SELF)
        if target is None:
            target = game.get_respawn_position()
        return self._choose_best(self._safe_directions(game), self._distance_to_key(game, target))

    def _pick_aggressive(self, game: GameApi) -> Direction:
        """Chases the opponent's trail for a kill if one's visible;
        otherwise cuts toward their territory to steal it on capture."""
        hunted = self._hunt_opponent_trail(game)
        if hunted is not None:
            return hunted
        target = self._nearest_territory(game, TerritoryView.OPPONENT)
        if target is None:
            target = game.get_agent_position()
        return self._choose_best(self._safe_directions(game), self._distance_to_key(game, target))

    def _hunt_opponent_trail(self, game: GameApi) -> Direction | None:
        """Shared by DEFENSIVE and AGGRESSIVE: a direction that closes on
        the opponent's visible trail, if one is visible at all."""
        target = self._nearest_occupant(game, OccupantView.OPPONENT_TRAIL)
        if target is None:
            return None
        return self._choose_best(self._huntable_directions(game), self._distance_to_key(game, target))

    def _pick_wandering(self, game: GameApi) -> Direction:
        """Picks at random among the directions whose open-space score is
        close to the best, so it's never fully predictable."""
        candidates = self._safe_directions(game)
        if not candidates:
            return self._fallback()
        best_score = max(self._open_neighbor_count(game, direction) for direction in candidates)
        good_enough = [
            direction for direction in candidates
            if self._open_neighbor_count(game, direction) >= best_score - _WANDER_OPENNESS_TOLERANCE
        ]
        return good_enough[self._random.randrange(len(good_enough))]

    def _pick_uniformly_random(self, game: GameApi) -> Direction:
        """Picks uniformly among every safe direction, with no bias toward
        open space at all — only used for the opening move."""
        candidates = self._safe_directions(game)
        if not candidates:
            return self._fallback()
        return candidates[self._random.randrange(len(candidates))]

    def _distance_to_key(self, game: GameApi, target: GridPosition):
        return lambda direction: manhattan_distance(self._destination(game, direction), target)

    def _most_open_first_key(self, game: GameApi):
        return lambda direction: -self._open_neighbor_count(game, direction)

    def _choose_best(self, candidates: list[Direction], ranking) -> Direction:
        if not candidates:
            return self._fallback()
        return min(candidates, key=ranking)

    # ---- Board reading -----------------------------------------------------

    def _safe_directions(self, game: GameApi) -> list[Direction]:
        """Directions that are in bounds and land on neither trail nor the
        opponent's agent."""
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
        trail — that's the point of hunting."""
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

    def _open_neighbor_count(self, game: GameApi, direction: Direction) -> int:
        """Count of on-board empty unowned cells cardinally adjacent to the
        destination. Off-board neighbors are not open."""
        destination = self._destination(game, direction)
        count = 0
        for neighbor_direction in Direction:
            neighbor = next_position(destination, neighbor_direction)
            if self._is_open(self._cell_at(game, neighbor)):
                count += 1
        return count

    def _nearest_occupant(self, game: GameApi, occupant: OccupantView) -> GridPosition | None:
        return self._nearest_visible(game, lambda cell: cell.occupant == occupant)

    def _nearest_territory(self, game: GameApi, territory: TerritoryView) -> GridPosition | None:
        return self._nearest_visible(game, lambda cell: cell.territory == territory)

    @staticmethod
    def _nearest_visible(game: GameApi, matches) -> GridPosition | None:
        origin = game.get_agent_position()
        best: GridPosition | None = None
        best_distance: int | None = None
        for row in game.get_visible_grid():
            for cell in row:
                if matches(cell):
                    distance = manhattan_distance(origin, cell.position)
                    if best_distance is None or distance < best_distance:
                        best_distance = distance
                        best = cell.position
        return best

    @staticmethod
    def _destination(game: GameApi, direction: Direction) -> GridPosition:
        return next_position(game.get_agent_position(), direction)

    @staticmethod
    def _cell_at(game: GameApi, position: GridPosition) -> VisibleCell | None:
        """None only when position is off the board (a corner or edge), not
        an open cell."""
        if not is_within_board(position, game.get_board_width(), game.get_board_height()):
            return None
        cell = find_cell(game.get_visible_grid(), position)
        return cell if cell is not None else VisibleCell(position, OccupantView.EMPTY, TerritoryView.UNOWNED)

    def _occupant_at(self, game: GameApi, position: GridPosition) -> OccupantView | None:
        cell = self._cell_at(game, position)
        return None if cell is None else cell.occupant

    def _territory_at(self, game: GameApi, position: GridPosition) -> TerritoryView | None:
        cell = self._cell_at(game, position)
        return None if cell is None else cell.territory

    @staticmethod
    def _is_open(cell: VisibleCell | None) -> bool:
        return cell is not None and cell.occupant == OccupantView.EMPTY and cell.territory == TerritoryView.UNOWNED

    def _fallback(self) -> Direction:
        return random_direction(self._random)
