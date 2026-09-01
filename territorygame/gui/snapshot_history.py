"""Cursor over snapshots the GUI has already received. Recording always
appends and jumps to live; back/forward only change which snapshot is
shown, never match state."""

from typing import Generic, TypeVar

T = TypeVar("T")


class SnapshotHistory(Generic[T]):
    def __init__(self) -> None:
        self._snapshots: list[T] = []
        self._index = -1

    def record(self, snapshot: T) -> None:
        self._snapshots.append(snapshot)
        self._index = len(self._snapshots) - 1

    def clear(self) -> None:
        self._snapshots.clear()
        self._index = -1

    def back(self, steps: int = 1) -> bool:
        moved = False
        for _ in range(steps):
            if self._index <= 0:
                return moved
            self._index -= 1
            moved = True
        return moved

    def forward(self, steps: int = 1) -> bool:
        moved = False
        for _ in range(steps):
            if self._index >= len(self._snapshots) - 1:
                return moved
            self._index += 1
            moved = True
        return moved

    def current(self) -> T:
        return self._snapshots[self._index]

    def can_go_back(self) -> bool:
        return self._index > 0

    def can_go_forward(self) -> bool:
        return 0 <= self._index < len(self._snapshots) - 1

    def is_at_live(self) -> bool:
        return self._index == len(self._snapshots) - 1

    def position(self) -> int:
        return self._index + 1

    def size(self) -> int:
        return len(self._snapshots)
