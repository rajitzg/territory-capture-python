"""Match configuration. Player count is implicit in
len(respawn_positions). Window sizes are full odd side lengths (e.g. 11
for an 11x11 visibility window), not radii.

Values are not hardcoded here; load_default() reads them from
game-config.properties (in territorygame/resources/), so board size,
visibility, turn count, respawn positions, and starting-territory shape
can all be changed by editing that file.

Values are validated in __post_init__ (every construction path runs it),
so a misconfiguration fails immediately with a clear message instead of
surfacing later as a confusing exception deep inside the engine."""

from dataclasses import dataclass
from pathlib import Path

from territorygame.api.grid_position import GridPosition
from territorygame.helpers.movement_utils import is_within_board

_DEFAULT_RESOURCE = Path(__file__).resolve().parent.parent / "resources" / "game-config.properties"


@dataclass(frozen=True)
class GameConfig:
    board_width: int
    board_height: int
    visibility_window_size: int
    turns_per_player: int
    respawn_positions: list[GridPosition]
    starting_territory_size: int
    autoplay_turn_delay_millis: int
    max_attempts_per_turn: int
    controller_seeds: list[int]

    def __post_init__(self) -> None:
        if self.board_width <= 0 or self.board_height <= 0:
            raise ValueError(
                f"board.width and board.height must be positive: {self.board_width}x{self.board_height}"
            )
        if self.visibility_window_size <= 0 or self.visibility_window_size % 2 == 0:
            raise ValueError(
                f"visibility.windowSize must be a positive odd number: {self.visibility_window_size}"
            )
        if self.visibility_window_size > self.board_width or self.visibility_window_size > self.board_height:
            raise ValueError(
                f"visibility.windowSize must not exceed the board dimensions: {self.visibility_window_size}"
            )
        if self.turns_per_player <= 0:
            raise ValueError(f"turns.perPlayer must be positive: {self.turns_per_player}")
        if self.starting_territory_size <= 0:
            raise ValueError(
                f"starting.territorySize must be positive: {self.starting_territory_size}"
            )
        if self.autoplay_turn_delay_millis < 0:
            raise ValueError(
                f"autoplay.turnDelayMillis must not be negative: {self.autoplay_turn_delay_millis}"
            )
        if self.max_attempts_per_turn <= 0:
            raise ValueError(
                f"turn.maxAttemptsPerTurn must be positive: {self.max_attempts_per_turn}"
            )
        respawn_positions = list(self.respawn_positions)
        object.__setattr__(self, "respawn_positions", respawn_positions)
        for position in respawn_positions:
            if not is_within_board(position, self.board_width, self.board_height):
                raise ValueError(f"Respawn position out of bounds: {position}")
        if _starting_territories_overlap(
            respawn_positions, self.starting_territory_size, self.board_width, self.board_height
        ):
            raise ValueError("Starting territories overlap for the configured respawn positions")
        controller_seeds = list(self.controller_seeds)
        object.__setattr__(self, "controller_seeds", controller_seeds)
        if len(controller_seeds) != len(respawn_positions):
            raise ValueError(
                "controllerSeeds must have exactly one entry per player: expected "
                f"{len(respawn_positions)}, got {len(controller_seeds)}"
            )

    @staticmethod
    def load_default() -> "GameConfig":
        return GameConfig.load_from_path(_DEFAULT_RESOURCE)

    @staticmethod
    def load_from_path(resource_path: Path) -> "GameConfig":
        return _from_properties(_parse_properties(resource_path))

    @staticmethod
    def starting_territory_around(
        center: GridPosition, size: int, width: int, height: int
    ) -> list[GridPosition]:
        """The square of cells (clipped to the board) centered on a respawn
        position. Shared by validation and match setup."""
        half = size // 2
        cells = []
        for y in range(center.y - half, center.y + half + 1):
            for x in range(center.x - half, center.x + half + 1):
                cell = GridPosition(x, y)
                if is_within_board(cell, width, height):
                    cells.append(cell)
        return cells


def _starting_territories_overlap(
    respawn_positions: list[GridPosition], size: int, width: int, height: int
) -> bool:
    seen: set[GridPosition] = set()
    for respawn_position in respawn_positions:
        for cell in GameConfig.starting_territory_around(respawn_position, size, width, height):
            if cell in seen:
                return True
            seen.add(cell)
    return False


def _parse_properties(resource_path: Path) -> dict[str, str]:
    if not resource_path.exists():
        raise FileNotFoundError(f"Config resource not found: {resource_path}")
    properties: dict[str, str] = {}
    for line in resource_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        properties[key.strip()] = value.strip()
    return properties


def _require_int(properties: dict[str, str], key: str) -> int:
    if key not in properties:
        raise KeyError(f"Missing required config key: {key}")
    return int(properties[key])


def _from_properties(properties: dict[str, str]) -> GameConfig:
    respawn_count = _require_int(properties, "respawn.count")
    respawn_positions = []
    controller_seeds = []
    for i in range(respawn_count):
        respawn_positions.append(
            GridPosition(_require_int(properties, f"respawn.{i}.x"), _require_int(properties, f"respawn.{i}.y"))
        )
        controller_seeds.append(_require_int(properties, f"controller.seed.{i}"))
    return GameConfig(
        board_width=_require_int(properties, "board.width"),
        board_height=_require_int(properties, "board.height"),
        visibility_window_size=_require_int(properties, "visibility.windowSize"),
        turns_per_player=_require_int(properties, "turns.perPlayer"),
        respawn_positions=respawn_positions,
        starting_territory_size=_require_int(properties, "starting.territorySize"),
        autoplay_turn_delay_millis=_require_int(properties, "autoplay.turnDelayMillis"),
        max_attempts_per_turn=_require_int(properties, "turn.maxAttemptsPerTurn"),
        controller_seeds=controller_seeds,
    )
