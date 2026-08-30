"""Test-only factory for small, deterministic two-player game states."""

from territorygame.api.grid_position import GridPosition
from territorygame.domain.agent import Agent
from territorygame.domain.board import Board
from territorygame.domain.game_state import GameState
from territorygame.domain.player import Player
from territorygame.domain.player_id import PlayerId


def two_player_state(
    width: int, height: int,
    position0: GridPosition, territory0: list[GridPosition],
    position1: GridPosition, territory1: list[GridPosition],
    turns_per_player: int,
) -> GameState:
    board = Board(width, height)
    id0, id1 = PlayerId(0), PlayerId(1)

    player0 = Player(id0, Agent(position0, position0), territory0)
    player1 = Player(id1, Agent(position1, position1), territory1)

    for cell in territory0:
        board.set_territory_owner(cell, id0)
    for cell in territory1:
        board.set_territory_owner(cell, id1)

    return GameState(board, [player0, player1], turns_per_player)
