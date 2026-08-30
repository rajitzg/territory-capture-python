"""Head/trail layer of a cell as seen by a viewing player. Agent wins over
trail on this layer only; territory is reported separately."""

from enum import Enum, auto


class OccupantView(Enum):
    EMPTY = auto()
    SELF_TRAIL = auto()
    OPPONENT_TRAIL = auto()
    SELF_AGENT = auto()
    OPPONENT_AGENT = auto()
