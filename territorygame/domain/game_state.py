"""Authoritative mutable match state: board, players, per-player remaining
turns, and whose turn it is. Never exposed to candidate or GUI code
directly. Assumes exactly two players, matching every rule in the spec
that refers to "the other agent" / "the opponent"."""

from territorygame.api.move_result import MoveResult
from territorygame.domain.board import Board
from territorygame.domain.player import Player
from territorygame.domain.player_id import PlayerId


class GameState:
    def __init__(self, board: Board, players: list[Player], turns_per_player: int) -> None:
        self._board = board
        self._players = list(players)
        self._remaining_turns: dict[PlayerId, int] = {}
        self._kill_counts: dict[PlayerId, int] = {}
        self._death_counts: dict[PlayerId, int] = {}
        for player in players:
            self._remaining_turns[player.get_id()] = turns_per_player
            self._kill_counts[player.get_id()] = 0
            self._death_counts[player.get_id()] = 0
        self._active_player_id = players[0].get_id()
        self._last_move_result: MoveResult | None = None
        self._last_turn_error: str | None = None

    def get_board(self) -> Board:
        return self._board

    def get_players(self) -> list[Player]:
        return list(self._players)

    def get_player(self, player_id: PlayerId) -> Player:
        for player in self._players:
            if player.get_id() == player_id:
                return player
        raise ValueError(f"Unknown player: {player_id}")

    def get_opponent(self, player_id: PlayerId) -> Player:
        """The other participant in this two-player match."""
        for player in self._players:
            if player.get_id() != player_id:
                return player
        raise ValueError(f"No opponent for: {player_id}")

    def get_active_player_id(self) -> PlayerId:
        return self._active_player_id

    def set_active_player_id(self, player_id: PlayerId) -> None:
        self._active_player_id = player_id

    def get_remaining_turns(self, player_id: PlayerId) -> int:
        return self._remaining_turns[player_id]

    def decrement_remaining_turns(self, player_id: PlayerId) -> None:
        self._remaining_turns[player_id] -= 1

    def is_game_over(self) -> bool:
        return all(turns <= 0 for turns in self._remaining_turns.values())

    def get_last_move_result(self) -> MoveResult | None:
        return self._last_move_result

    def set_last_move_result(self, result: MoveResult | None) -> None:
        self._last_move_result = result

    def get_kill_count(self, player_id: PlayerId) -> int:
        return self._kill_counts[player_id]

    def increment_kill_count(self, player_id: PlayerId) -> None:
        self._kill_counts[player_id] += 1

    def get_death_count(self, player_id: PlayerId) -> int:
        return self._death_counts[player_id]

    def increment_death_count(self, player_id: PlayerId) -> None:
        self._death_counts[player_id] += 1

    def get_last_turn_error(self) -> str | None:
        """Display-only description of why the most recent turn produced no
        successful move, if any."""
        return self._last_turn_error

    def set_last_turn_error(self, message: str | None) -> None:
        self._last_turn_error = message
