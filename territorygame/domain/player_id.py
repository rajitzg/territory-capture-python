"""Opaque identity for a participant. Never a stand-in for "player 1"/"player 2" naming."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerId:
    index: int
