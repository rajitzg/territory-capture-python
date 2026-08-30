"""One cell of a GameApi.get_visible_grid() window, with its absolute position."""

from dataclasses import dataclass

from territorygame.api.grid_position import GridPosition
from territorygame.api.occupant_view import OccupantView
from territorygame.api.territory_view import TerritoryView


@dataclass(frozen=True)
class VisibleCell:
    position: GridPosition
    occupant: OccupantView
    territory: TerritoryView
