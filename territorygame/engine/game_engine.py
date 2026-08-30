"""Coordinates a match: lifecycle, turn order, controller invocation, the
end condition, and observer notification. Implements no capture logic,
visibility generation, or rendering.

Java uses a single-thread ExecutorService so start/pause/step/reset
commands run one at a time, off the Swing EDT, with volatile fields for
cross-thread visibility. This port uses one background threading.Thread
pulling callables off a queue.Queue (FIFO, single consumer — same
ordering guarantee as a single-thread executor) and relies on CPython's
GIL for the same visibility guarantee Java gets from volatile on simple
attribute reads/writes — no additional locking, matching the Java source
exactly (it doesn't lock either)."""

import queue
import threading
import time
import traceback
from typing import Callable

from territorygame.api.agent_controller import AgentController
from territorygame.api.grid_position import GridPosition
from territorygame.domain.agent import Agent
from territorygame.domain.board import Board
from territorygame.domain.game_config import GameConfig
from territorygame.domain.game_state import GameState
from territorygame.domain.player import Player
from territorygame.domain.player_id import PlayerId
from territorygame.engine.game_api_impl import GameApiImpl
from territorygame.engine.game_observer import GameObserver
from territorygame.engine.game_snapshot import CellSnapshot, GameSnapshot, PlayerSnapshot
from territorygame.engine.turn_manager import TurnManager
from territorygame.rules.move_resolver import MoveResolver
from territorygame.rules.respawn_service import RespawnService
from territorygame.rules.territory_resolver import TerritoryResolver
from territorygame.visibility.visibility_service import VisibilityService


class GameEngine:
    def __init__(self, config: GameConfig, controllers_in_player_order: list[AgentController]) -> None:
        self._config = config
        self._turn_manager = TurnManager(config.max_attempts_per_turn)
        self._turn_delay_millis = config.autoplay_turn_delay_millis
        self._controllers_in_player_order = list(controllers_in_player_order)
        self._observers: list[GameObserver] = []
        self._task_queue: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self._running = False
        self._halted = False
        self._halt_message: str | None = None
        self._controllers: dict[PlayerId, AgentController] = {}
        self._apis: dict[PlayerId, GameApiImpl] = {}

        self._build_fresh_match()

        self._worker = threading.Thread(target=self._run_worker, name="game-engine-thread", daemon=True)
        self._worker.start()

    def add_observer(self, observer: GameObserver) -> None:
        self._observers.append(observer)

    def set_turn_delay_millis(self, turn_delay_millis: int) -> None:
        """Changes the pause between turns during continuous play (see
        start()). Takes effect from the next turn on."""
        self._turn_delay_millis = turn_delay_millis

    def set_controller(self, player_index: int, controller: AgentController) -> None:
        """Replaces the controller for one player slot (0-based, matching
        the order passed to the constructor/reset) without resetting the
        match — position, territory, trail, and turns are all left as they
        are. Takes effect from that player's next turn on."""

        def task() -> None:
            updated = list(self._controllers_in_player_order)
            updated[player_index] = controller
            self._controllers_in_player_order = updated
            player_id = self._state.get_players()[player_index].get_id()
            self._controllers[player_id] = controller

        self._submit_safely(task)

    def start(self) -> None:
        """Runs turns continuously until paused or the match ends. No-op if
        already running or halted."""
        if self._running or self._halted:
            return
        self._running = True
        self._submit_safely(self._run_until_paused_or_over)

    def pause(self) -> None:
        """Stops the run loop after the in-flight turn finishes."""
        self._running = False

    def step(self) -> None:
        """Runs exactly one turn, regardless of the running flag. No-op if halted."""

        def task() -> None:
            if not self._halted and not self._state.is_game_over():
                self._run_single_turn_and_publish()

        self._submit_safely(task)

    def reset(self, controllers_in_player_order: list[AgentController] | None = None) -> None:
        """Rebuilds a fresh match, keeping the current controllers by
        default, or with a new set (e.g. after the GUI's slot selection
        changes) if given one."""
        new_controllers = list(
            controllers_in_player_order
            if controllers_in_player_order is not None
            else self._controllers_in_player_order
        )

        def task() -> None:
            self._running = False
            self._halted = False
            self._halt_message = None
            self._controllers_in_player_order = new_controllers
            self._build_fresh_match()
            self._publish(self._build_snapshot())

        self._submit_safely(task)

    def _run_until_paused_or_over(self) -> None:
        while self._running and not self._state.is_game_over():
            self._run_single_turn_and_publish()
            if self._running:
                self._pause_between_turns()
        self._running = False

    def _run_worker(self) -> None:
        while True:
            task = self._task_queue.get()
            task()

    def _submit_safely(self, task: Callable[[], None]) -> None:
        """Puts a task on the background worker's queue, guarding against
        any exception that isn't already contained by TurnManager (e.g. a
        bug in the engine's own plumbing rather than a controller). Without
        this, such an exception would kill the worker thread silently and
        the match would just stop updating with no visible cause."""

        def guarded() -> None:
            try:
                task()
            except Exception as e:  # mirrors Java's catch (Throwable t)
                self._handle_fatal_error(e)

        self._task_queue.put(guarded)

    def _handle_fatal_error(self, error: Exception) -> None:
        self._running = False
        self._halted = True
        self._halt_message = f"Internal engine error: {error}"
        traceback.print_exc()
        try:
            self._publish(self._build_snapshot())
        except Exception:
            pass  # build_snapshot()/publish() itself is what's broken; nothing more we can safely do.

    def _pause_between_turns(self) -> None:
        """Paces continuous play so a match is watchable instead of finishing
        instantly. Step bypasses this entirely."""
        time.sleep(self._turn_delay_millis / 1000)

    def _run_single_turn_and_publish(self) -> None:
        self._turn_manager.execute_turn(self._state, self._controllers, self._apis)
        if self._state.get_last_turn_error() is not None:
            print(self._state.get_last_turn_error())
        self._publish(self._build_snapshot())

    def _build_fresh_match(self) -> None:
        board = Board(self._config.board_width, self._config.board_height)
        players: list[Player] = []
        for i, respawn_position in enumerate(self._config.respawn_positions):
            player_id = PlayerId(i)
            starting_territory = GameConfig.starting_territory_around(
                respawn_position, self._config.starting_territory_size,
                self._config.board_width, self._config.board_height,
            )
            for cell in starting_territory:
                board.set_territory_owner(cell, player_id)
            players.append(Player(player_id, Agent(respawn_position, respawn_position), starting_territory))

        self._state = GameState(board, players, self._config.turns_per_player)

        move_resolver = MoveResolver(RespawnService(), TerritoryResolver())
        visibility_service = VisibilityService(self._config.visibility_window_size)

        self._controllers = {}
        self._apis = {}
        for i, player in enumerate(players):
            player_id = player.get_id()
            self._controllers[player_id] = self._controllers_in_player_order[i]
            self._apis[player_id] = GameApiImpl(self._state, player_id, move_resolver, visibility_service)

    def _publish(self, snapshot: GameSnapshot) -> None:
        for observer in self._observers:
            observer.on_game_state_changed(snapshot)

    def _build_snapshot(self) -> GameSnapshot:
        board = self._state.get_board()
        width = board.get_width()
        height = board.get_height()

        cells = tuple(
            tuple(
                CellSnapshot(board.territory_owner_at(GridPosition(x, y)), board.trail_owner_at(GridPosition(x, y)))
                for x in range(width)
            )
            for y in range(height)
        )

        player_snapshots = tuple(
            PlayerSnapshot(
                player.get_id(),
                player.get_agent().get_position(),
                board.territory_count(player.get_id()),
                self._state.get_kill_count(player.get_id()),
                self._state.get_death_count(player.get_id()),
                self._state.get_remaining_turns(player.get_id()),
                tuple(player.get_agent().get_active_trail()),
                self._controllers[player.get_id()].get_debug_state(),
            )
            for player in self._state.get_players()
        )

        error_message = self._halt_message if self._halted else self._state.get_last_turn_error()
        return GameSnapshot(
            width, height, cells, player_snapshots,
            self._state.get_active_player_id(), self._state.get_last_move_result(),
            self._config.visibility_window_size, self._state.is_game_over(), error_message,
        )
