"""The moving piece a player controls: its position, configured respawn
point, and ordered active trail. Holds no decision-making strategy.

Mutators are public for use by the rules/engine modules. The
candidate-facing boundary is preserved not by access control but by never
handing an Agent reference to candidate code or the GUI."""

from territorygame.api.grid_position import GridPosition


class Agent:
    def __init__(self, position: GridPosition, respawn_position: GridPosition) -> None:
        self._position = position
        self._respawn_position = respawn_position
        self._active_trail: list[GridPosition] = []

    def get_position(self) -> GridPosition:
        return self._position

    def set_position(self, position: GridPosition) -> None:
        self._position = position

    def get_respawn_position(self) -> GridPosition:
        return self._respawn_position

    def get_active_trail(self) -> list[GridPosition]:
        return list(self._active_trail)

    def is_trail_empty(self) -> bool:
        return len(self._active_trail) == 0

    def append_trail(self, cell: GridPosition) -> None:
        self._active_trail.append(cell)

    def clear_trail(self) -> None:
        self._active_trail.clear()
