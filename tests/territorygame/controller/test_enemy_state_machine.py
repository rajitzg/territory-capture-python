import queue

from territorygame.api.direction import Direction
from territorygame.api.game_api import GameApi
from territorygame.api.grid_position import GridPosition
from territorygame.api.move_result import MoveResult
from territorygame.api.occupant_view import OccupantView
from territorygame.api.territory_view import TerritoryView
from territorygame.api.visible_cell import VisibleCell
from territorygame.controller.enemy_state_machine import EnemyStateMachine
from territorygame.domain.game_config import GameConfig
from territorygame.engine.game_engine import GameEngine
from territorygame.engine.game_observer import GameObserver
from territorygame.helpers.movement_utils import next_position


def test_chebyshev_distance_is_the_larger_axis_delta():
    assert EnemyStateMachine.chebyshev_distance(GridPosition(0, 0), GridPosition(3, 1)) == 3
    assert EnemyStateMachine.chebyshev_distance(GridPosition(5, 5), GridPosition(4, 3)) == 2
    assert EnemyStateMachine.chebyshev_distance(GridPosition(2, 2), GridPosition(2, 2)) == 0


def test_empty_trail_always_fits_regardless_of_grid_size():
    assert EnemyStateMachine.fits_safety_grid(GridPosition(10, 10), [], 1)


def test_trail_fits_when_every_cell_is_within_half_the_grid_size_of_the_head():
    head = GridPosition(5, 5)
    trail = [GridPosition(5, 4), GridPosition(5, 5)]

    assert EnemyStateMachine.fits_safety_grid(head, trail, 5)  # half = 2, distance = 1


def test_trail_does_not_fit_when_any_cell_exceeds_half_the_grid_size():
    head = GridPosition(5, 5)
    trail = [GridPosition(2, 5), GridPosition(5, 5)]  # distance 3

    assert not EnemyStateMachine.fits_safety_grid(head, trail, 5)  # half = 2


def test_opposite_returns_the_reverse_cardinal_direction():
    assert EnemyStateMachine.opposite(Direction.NORTH) == Direction.SOUTH
    assert EnemyStateMachine.opposite(Direction.SOUTH) == Direction.NORTH
    assert EnemyStateMachine.opposite(Direction.EAST) == Direction.WEST
    assert EnemyStateMachine.opposite(Direction.WEST) == Direction.EAST


def test_perpendicular_options_for_north_south_are_east_west():
    assert EnemyStateMachine.perpendicular_options(Direction.NORTH) == [Direction.EAST, Direction.WEST]
    assert EnemyStateMachine.perpendicular_options(Direction.SOUTH) == [Direction.EAST, Direction.WEST]


def test_perpendicular_options_for_east_west_are_north_south():
    assert EnemyStateMachine.perpendicular_options(Direction.EAST) == [Direction.NORTH, Direction.SOUTH]
    assert EnemyStateMachine.perpendicular_options(Direction.WEST) == [Direction.NORTH, Direction.SOUTH]


def test_mirror_back_walks_the_opposite_of_out_direction_for_steps_out_steps():
    position = GridPosition(5, 3)  # 2 north, then 3 east of a (5,5) start
    mirrored = EnemyStateMachine.mirror_back(position, Direction.NORTH, 2)

    assert mirrored == GridPosition(5, 5)  # 2 steps south (opposite of north) from (5,3)


def test_mirror_back_with_zero_steps_returns_the_same_position():
    position = GridPosition(7, 7)

    assert EnemyStateMachine.mirror_back(position, Direction.EAST, 0) == position


def test_is_vertical_is_true_only_for_north_and_south():
    assert EnemyStateMachine.is_vertical(Direction.NORTH)
    assert EnemyStateMachine.is_vertical(Direction.SOUTH)
    assert not EnemyStateMachine.is_vertical(Direction.EAST)
    assert not EnemyStateMachine.is_vertical(Direction.WEST)


class StubGameApi(GameApi):
    def __init__(self, position: GridPosition, respawn: GridPosition, visible_grid: list[list[VisibleCell]]) -> None:
        self.position = position
        self._respawn = respawn
        self.visible_grid = visible_grid
        self.active_trail: list[GridPosition] = []
        self.moved_direction: Direction | None = None

    def get_agent_position(self) -> GridPosition:
        return self.position

    def get_respawn_position(self) -> GridPosition:
        return self._respawn

    def get_owned_territory_cell_count(self) -> int:
        return 25

    def get_opponent_territory_cell_count(self) -> int:
        return 0

    def get_remaining_turns(self) -> int:
        return 1

    def get_active_trail(self) -> list[GridPosition]:
        return self.active_trail

    def get_visible_grid(self):
        return self.visible_grid

    def get_board_width(self) -> int:
        return len(self.visible_grid[0])

    def get_board_height(self) -> int:
        return len(self.visible_grid)

    def move(self, direction: Direction) -> MoveResult:
        self.moved_direction = direction
        return MoveResult.MOVED


def _filled_grid(territory: TerritoryView, size: int = 5) -> list[list[VisibleCell]]:
    return [
        [VisibleCell(GridPosition(x, y), OccupantView.EMPTY, territory) for x in range(size)]
        for y in range(size)
    ]


def test_reposition_keeps_its_random_direction_while_valid():
    grid = _filled_grid(TerritoryView.SELF, 7)
    game = StubGameApi(GridPosition(3, 3), GridPosition(0, 3), grid)
    controller = EnemyStateMachine()

    controller.take_turn(game)
    committed = game.moved_direction

    game.position = next_position(game.position, committed)
    controller.take_turn(game)

    assert controller.get_debug_state() == "REPOSITION"
    assert game.moved_direction == committed


def test_reposition_commits_to_non_self_territory_within_three_cells():
    # Java's equivalent test places the opponent-territory cell 3 EAST of
    # the start, because Java's Random(42) picks EAST as the uniformly
    # random direction on the first call (no candidate is within lookahead
    # yet, so every safe direction is equally eligible). Python's
    # random.Random(42) is a different PRNG algorithm — cross-language RNG
    # reproducibility was explicitly out of scope for this port — and picks
    # NORTH for the same call. The geometry here is rotated 90 degrees
    # (EAST -> NORTH, and the off-ray distractor's offset rotated to match)
    # so the same commit/re-affirm/transition-to-OUT narrative holds.
    grid = _filled_grid(TerritoryView.SELF, 7)
    grid[0][3] = VisibleCell(GridPosition(3, 0), OccupantView.EMPTY, TerritoryView.OPPONENT)
    grid[2][2] = VisibleCell(GridPosition(2, 2), OccupantView.EMPTY, TerritoryView.UNOWNED)
    game = StubGameApi(GridPosition(3, 3), GridPosition(0, 3), grid)
    controller = EnemyStateMachine()

    controller.take_turn(game)
    assert controller.get_debug_state() == "REPOSITION"
    assert game.moved_direction == Direction.NORTH

    game.position = GridPosition(3, 2)
    controller.take_turn(game)
    assert controller.get_debug_state() == "REPOSITION"
    assert game.moved_direction == Direction.NORTH

    game.position = GridPosition(3, 1)
    controller.take_turn(game)
    assert controller.get_debug_state() == "OUT"
    assert game.moved_direction == Direction.NORTH


def test_reposition_prefers_the_nearest_non_self_ray():
    grid = _filled_grid(TerritoryView.SELF, 7)
    grid[0][3] = VisibleCell(GridPosition(3, 0), OccupantView.EMPTY, TerritoryView.UNOWNED)
    grid[3][5] = VisibleCell(GridPosition(5, 3), OccupantView.EMPTY, TerritoryView.OPPONENT)
    game = StubGameApi(GridPosition(3, 3), GridPosition(0, 3), grid)

    EnemyStateMachine().take_turn(game)

    assert game.moved_direction == Direction.EAST


def test_reposition_prefers_vertical_when_nearest_rays_tie():
    grid = _filled_grid(TerritoryView.SELF, 7)
    grid[1][3] = VisibleCell(GridPosition(3, 1), OccupantView.EMPTY, TerritoryView.UNOWNED)
    grid[3][5] = VisibleCell(GridPosition(5, 3), OccupantView.EMPTY, TerritoryView.OPPONENT)
    game = StubGameApi(GridPosition(3, 3), GridPosition(0, 3), grid)

    EnemyStateMachine().take_turn(game)

    assert game.moved_direction == Direction.NORTH


def test_out_prefers_vertical_among_adjacent_non_self_directions():
    grid = _filled_grid(TerritoryView.SELF, 7)
    grid[2][3] = VisibleCell(GridPosition(3, 2), OccupantView.EMPTY, TerritoryView.OPPONENT)
    grid[3][4] = VisibleCell(GridPosition(4, 3), OccupantView.EMPTY, TerritoryView.OPPONENT)
    for y in range(3, 7):
        for x in range(5, 7):
            grid[y][x] = VisibleCell(GridPosition(x, y), OccupantView.EMPTY, TerritoryView.UNOWNED)
    game = StubGameApi(GridPosition(3, 3), GridPosition(0, 3), grid)

    EnemyStateMachine().take_turn(game)

    assert game.moved_direction == Direction.NORTH


def test_out_can_start_onto_opponent_territory():
    grid = _filled_grid(TerritoryView.SELF)
    for x in range(5):
        grid[0][x] = VisibleCell(GridPosition(x, 0), OccupantView.EMPTY, TerritoryView.UNOWNED)
    grid[2][3] = VisibleCell(GridPosition(3, 2), OccupantView.EMPTY, TerritoryView.OPPONENT)
    game = StubGameApi(GridPosition(2, 2), GridPosition(0, 2), grid)
    controller = EnemyStateMachine()

    controller.take_turn(game)

    assert controller.get_debug_state() == "OUT"
    assert game.moved_direction == Direction.EAST


def test_out_stops_before_moving_back_onto_owned_territory():
    grid = _filled_grid(TerritoryView.SELF)
    grid[2][3] = VisibleCell(GridPosition(3, 2), OccupantView.EMPTY, TerritoryView.OPPONENT)
    game = StubGameApi(GridPosition(2, 2), GridPosition(0, 2), grid)
    controller = EnemyStateMachine()

    controller.take_turn(game)
    assert game.moved_direction == Direction.EAST

    game.position = GridPosition(3, 2)
    game.active_trail = [GridPosition(2, 2)]
    controller.take_turn(game)

    assert controller.get_debug_state() == "ACROSS"
    assert game.moved_direction in (Direction.NORTH, Direction.SOUTH)


def test_across_chooses_the_perpendicular_direction_with_an_owned_mirror():
    grid = _filled_grid(TerritoryView.SELF, 7)
    grid[3][3] = VisibleCell(GridPosition(3, 3), OccupantView.EMPTY, TerritoryView.OPPONENT)
    game = StubGameApi(GridPosition(2, 3), GridPosition(0, 3), grid)
    controller = EnemyStateMachine()

    controller.take_turn(game)
    assert game.moved_direction == Direction.EAST

    grid[2][2] = VisibleCell(GridPosition(2, 2), OccupantView.EMPTY, TerritoryView.UNOWNED)
    game.position = GridPosition(3, 3)
    game.active_trail = [GridPosition(3, 3)]
    controller.take_turn(game)

    assert controller.get_debug_state() == "ACROSS"
    assert game.moved_direction == Direction.SOUTH


def test_back_retraces_opposite_of_out_direction():
    grid = _filled_grid(TerritoryView.SELF, 7)
    grid[3][3] = VisibleCell(GridPosition(3, 3), OccupantView.EMPTY, TerritoryView.UNOWNED)
    grid[3][4] = VisibleCell(GridPosition(4, 3), OccupantView.EMPTY, TerritoryView.UNOWNED)
    game = StubGameApi(GridPosition(2, 3), GridPosition(0, 3), grid)
    controller = EnemyStateMachine()

    controller.take_turn(game)
    assert game.moved_direction == Direction.EAST

    game.position = GridPosition(3, 3)
    game.active_trail = [GridPosition(2, 3)]
    controller.take_turn(game)
    assert game.moved_direction == Direction.EAST

    grid[2][2] = VisibleCell(GridPosition(2, 2), OccupantView.EMPTY, TerritoryView.UNOWNED)
    grid[4][3] = VisibleCell(GridPosition(3, 4), OccupantView.EMPTY, TerritoryView.UNOWNED)
    grid[4][4] = VisibleCell(GridPosition(4, 4), OccupantView.EMPTY, TerritoryView.UNOWNED)
    game.position = GridPosition(4, 3)
    game.active_trail = [GridPosition(2, 3), GridPosition(3, 3)]
    controller.take_turn(game)
    assert controller.get_debug_state() == "ACROSS"
    assert game.moved_direction == Direction.SOUTH

    grid[5][2] = VisibleCell(GridPosition(2, 5), OccupantView.EMPTY, TerritoryView.UNOWNED)
    game.position = GridPosition(4, 4)
    game.active_trail = [
        GridPosition(2, 3), GridPosition(3, 3), GridPosition(4, 3), GridPosition(4, 4)
    ]
    controller.take_turn(game)

    assert controller.get_debug_state() == "BACK"
    assert game.moved_direction == Direction.WEST


def test_blocked_territory_edge_repositions_instead_of_starting_out():
    grid = _filled_grid(TerritoryView.SELF)
    grid[2][3] = VisibleCell(GridPosition(3, 2), OccupantView.OPPONENT_TRAIL, TerritoryView.OPPONENT)
    game = StubGameApi(GridPosition(2, 2), GridPosition(0, 2), grid)
    controller = EnemyStateMachine()

    controller.take_turn(game)

    assert controller.get_debug_state() == "REPOSITION"
    assert game.moved_direction in (Direction.NORTH, Direction.SOUTH, Direction.WEST)


class _QueueObserver(GameObserver):
    def __init__(self, snapshots: "queue.Queue") -> None:
        self._snapshots = snapshots

    def on_game_state_changed(self, snapshot) -> None:
        self._snapshots.put(snapshot)


def test_plays_many_turns_against_itself_without_framework_errors():
    config = GameConfig(20, 20, 11, 40, [GridPosition(4, 10), GridPosition(15, 10)], 3, 0, 20, [1, 2])
    controllers = [EnemyStateMachine(), EnemyStateMachine()]
    engine = GameEngine(config, controllers)
    snapshots: "queue.Queue" = queue.Queue()
    engine.add_observer(_QueueObserver(snapshots))
    engine.reset(controllers)
    assert snapshots.get(timeout=2) is not None

    engine.start()

    last = None
    for _ in range(80):  # 40 turns per player, 2 players
        snapshot = snapshots.get(timeout=2)
        assert snapshot is not None
        last = snapshot

    assert last.game_over
