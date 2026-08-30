"""Player-scoped view of the game a controller uses to observe state and
move. Implementations must never leak authoritative backend types or
mutable references."""

from abc import ABC, abstractmethod

from territorygame.api.direction import Direction
from territorygame.api.grid_position import GridPosition
from territorygame.api.move_result import MoveResult
from territorygame.api.visible_cell import VisibleCell


class GameApi(ABC):

    @abstractmethod
    def get_agent_position(self) -> GridPosition: ...

    @abstractmethod
    def get_respawn_position(self) -> GridPosition: ...

    @abstractmethod
    def get_owned_territory_cell_count(self) -> int: ...

    @abstractmethod
    def get_opponent_territory_cell_count(self) -> int: ...

    @abstractmethod
    def get_remaining_turns(self) -> int: ...

    @abstractmethod
    def get_active_trail(self) -> list[GridPosition]:
        """The player's current active trail, ordered oldest to newest."""

    @abstractmethod
    def get_visible_grid(self) -> tuple[tuple[VisibleCell, ...], ...]:
        """Cells visible around the agent, indexed [row][column] i.e. [y][x] within the window."""

    @abstractmethod
    def get_board_width(self) -> int: ...

    @abstractmethod
    def get_board_height(self) -> int: ...

    @abstractmethod
    def move(self, direction: Direction) -> MoveResult: ...
