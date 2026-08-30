"""One board cell's ownership state. A cell may have a territory owner and a
different player's trail owner at the same time — a trail can cross free
space or enemy territory before it closes."""

from territorygame.domain.player_id import PlayerId


class BoardCell:
    def __init__(self) -> None:
        self._territory_owner: PlayerId | None = None
        self._trail_owner: PlayerId | None = None

    def get_territory_owner(self) -> PlayerId | None:
        return self._territory_owner

    def set_territory_owner(self, owner: PlayerId | None) -> None:
        self._territory_owner = owner

    def get_trail_owner(self) -> PlayerId | None:
        return self._trail_owner

    def set_trail_owner(self, owner: PlayerId | None) -> None:
        self._trail_owner = owner
