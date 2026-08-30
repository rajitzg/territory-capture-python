"""Territory layer of a cell as seen by a viewing player. Independent of
whether an agent or trail is also on the cell."""

from enum import Enum, auto


class TerritoryView(Enum):
    UNOWNED = auto()
    SELF = auto()
    OPPONENT = auto()
