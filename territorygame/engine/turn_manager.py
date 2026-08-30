"""Executes exactly one turn for the current active player, re-invoking
their controller until a successful move is made, then advances to the
next player with turns remaining.

A controller that throws, or that never manages a successful move within
max_attempts_per_turn attempts, forfeits just that turn rather than
hanging the match: the reason is recorded on GameState for the GUI/console
to surface, and play continues with the next player."""

from territorygame.api.agent_controller import AgentController
from territorygame.api.move_result import MoveResult
from territorygame.domain.game_state import GameState
from territorygame.domain.player import Player
from territorygame.domain.player_id import PlayerId
from territorygame.engine.game_api_impl import GameApiImpl


class TurnManager:
    def __init__(self, max_attempts_per_turn: int) -> None:
        self._max_attempts_per_turn = max_attempts_per_turn

    def execute_turn(
        self,
        state: GameState,
        controllers: dict[PlayerId, AgentController],
        apis: dict[PlayerId, GameApiImpl],
    ) -> None:
        active_id = state.get_active_player_id()
        api = apis[active_id]
        controller = controllers[active_id]

        api.reset_for_new_turn()
        state.set_last_turn_error(None)
        attempts = 0
        while not api.was_move_made_this_turn() and attempts < self._max_attempts_per_turn:
            attempts += 1
            try:
                controller.take_turn(api)
            except Exception as e:  # mirrors Java's catch (RuntimeException e)
                state.set_last_turn_error(f"Player {active_id.index}'s turn failed: {e}")
                break

        if api.was_move_made_this_turn():
            state.set_last_move_result(api.get_last_result_this_turn())
        else:
            state.decrement_remaining_turns(active_id)
            state.set_last_move_result(MoveResult.INVALID)
            if state.get_last_turn_error() is None:
                state.set_last_turn_error(
                    f"Player {active_id.index}'s controller made no successful move "
                    f"after {self._max_attempts_per_turn} attempts"
                )
        self._advance_active_player(state)

    def _advance_active_player(self, state: GameState) -> None:
        players = state.get_players()
        current_index = self._index_of(players, state.get_active_player_id())
        for offset in range(1, len(players) + 1):
            candidate = players[(current_index + offset) % len(players)].get_id()
            if state.get_remaining_turns(candidate) > 0:
                state.set_active_player_id(candidate)
                return
        # No player has turns remaining; leave active_player_id as-is, the
        # engine's run loop stops once state.is_game_over() is True.

    @staticmethod
    def _index_of(players: list[Player], player_id: PlayerId) -> int:
        for i, player in enumerate(players):
            if player.get_id() == player_id:
                return i
        raise ValueError(f"Active player not found: {player_id}")
