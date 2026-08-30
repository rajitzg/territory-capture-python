"""Top-level pygame application: lets the user pick which controller
occupies each player slot and drives Start/Pause/Step/Reset. Contains no
game-rule logic; every update arrives as an immutable GameSnapshot from
the engine's background thread and is picked up here once per frame on
the main thread. The pygame analogue of GameWindow.java.

Swing's invokeLater has no pygame equivalent, so instead the latest
snapshot is stashed behind a lock by on_game_state_changed() (called from
the engine's background thread) and read once per frame by the main
loop — same non-blocking, always-render-the-latest-available-state
behavior, different mechanism."""

import threading

import pygame

from territorygame.controller.available_controllers import ALL as CONTROLLER_OPTIONS
from territorygame.domain.game_config import GameConfig
from territorygame.engine.game_engine import GameEngine
from territorygame.engine.game_observer import GameObserver
from territorygame.engine.game_snapshot import GameSnapshot
from territorygame.gui.board_renderer import AGENT_COLORS, draw_board

_BACKGROUND = (255, 255, 255)
_TEXT_COLOR = (20, 20, 20)
_ERROR_BG = (255, 225, 225)
_ERROR_TEXT = (150, 0, 0)
_BUTTON_BG = (230, 230, 230)
_BUTTON_BORDER = (150, 150, 150)
_SIDE_PANEL_WIDTH = 300
_TOP_BAR_HEIGHT = 90
_STATUS_BAR_HEIGHT = 40
_MAX_BOARD_PIXELS = 800
_MIN_TURN_DELAY_MILLIS = 0
_MAX_TURN_DELAY_MILLIS = 500
# Slider travel is 0-1000; delay is mapped through a square curve so the
# fast end isn't cramped into a tiny fraction of the track (same curve
# Java's GameWindow used).
_SPEED_SLIDER_MAX = 1000


def _delay_to_slider(delay_millis: int) -> int:
    return round((delay_millis / _MAX_TURN_DELAY_MILLIS) ** 0.5 * _SPEED_SLIDER_MAX)


def _slider_to_delay(slider_value: int) -> int:
    t = slider_value / _SPEED_SLIDER_MAX
    return round(t * t * _MAX_TURN_DELAY_MILLIS)


class _SnapshotSink(GameObserver):
    """Receives snapshots on the engine's background thread; the main loop
    reads the latest one each frame under a lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: GameSnapshot | None = None

    def on_game_state_changed(self, snapshot: GameSnapshot) -> None:
        with self._lock:
            self._latest = snapshot

    def latest(self) -> GameSnapshot | None:
        with self._lock:
            return self._latest


class _Button:
    def __init__(self, rect: pygame.Rect, label: str, on_click) -> None:
        self.rect = rect
        self.label = label
        self.on_click = on_click

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(surface, _BUTTON_BG, self.rect)
        pygame.draw.rect(surface, _BUTTON_BORDER, self.rect, width=1)
        text = font.render(self.label, True, _TEXT_COLOR)
        surface.blit(text, text.get_rect(center=self.rect.center))

    def handle_click(self, position: tuple[int, int]) -> None:
        if self.rect.collidepoint(position):
            self.on_click()


class _Slider:
    """Horizontal drag slider — pygame has no built-in JSlider equivalent,
    so this is a minimal hand-rolled one: a track, a round handle, and
    click-or-drag-to-set-value, matching Swing's JSlider closely enough to
    stand in for it."""

    def __init__(self, rect: pygame.Rect, min_value: int, max_value: int, initial_value: int, on_change) -> None:
        self.rect = rect
        self._min_value = min_value
        self._max_value = max_value
        self._value = initial_value
        self._on_change = on_change
        self._dragging = False

    @property
    def value(self) -> int:
        return self._value

    def _value_from_x(self, x: int) -> int:
        t = (x - self.rect.x) / self.rect.width
        t = max(0.0, min(1.0, t))
        return round(self._min_value + t * (self._max_value - self._min_value))

    def _handle_x(self) -> int:
        t = (self._value - self._min_value) / (self._max_value - self._min_value)
        return self.rect.x + round(t * self.rect.width)

    def handle_mouse_down(self, position: tuple[int, int]) -> None:
        # A generous vertical hit area around the thin track, since the
        # visible line is only a few pixels tall.
        hit_rect = self.rect.inflate(0, 16)
        if hit_rect.collidepoint(position):
            self._dragging = True
            self._set_value(self._value_from_x(position[0]))

    def handle_mouse_motion(self, position: tuple[int, int]) -> None:
        if self._dragging:
            self._set_value(self._value_from_x(position[0]))

    def handle_mouse_up(self) -> None:
        self._dragging = False

    def _set_value(self, value: int) -> None:
        if value != self._value:
            self._value = value
            self._on_change(value)

    def draw(self, surface: pygame.Surface) -> None:
        track_y = self.rect.centery
        pygame.draw.line(surface, _BUTTON_BORDER, (self.rect.x, track_y), (self.rect.right, track_y), 3)
        handle_x = self._handle_x()
        pygame.draw.circle(surface, (90, 90, 90), (handle_x, track_y), 7)
        pygame.draw.circle(surface, (255, 255, 255), (handle_x, track_y), 4)


class _ControllerPicker(_Button):
    """Clicking cycles through CONTROLLER_OPTIONS for one player slot —
    the pygame stand-in for Swing's JComboBox, since pygame has no
    built-in dropdown widget."""

    def __init__(self, rect: pygame.Rect, initial_index: int, on_change) -> None:
        self._index = initial_index
        self._on_change = on_change
        super().__init__(rect, "", self._cycle)
        self.label = self._label()

    def _label(self) -> str:
        return f"Player: {CONTROLLER_OPTIONS[self._index].label}"

    def _cycle(self) -> None:
        self._index = (self._index + 1) % len(CONTROLLER_OPTIONS)
        self.label = self._label()
        self._on_change(self._index)

    @property
    def index(self) -> int:
        return self._index


class GameWindow:
    def __init__(self, config: GameConfig) -> None:
        pygame.init()
        pygame.display.set_caption("Territory Capture")
        self._config = config
        self._font = pygame.font.SysFont(None, 20)
        self._bold_font = pygame.font.SysFont(None, 22, bold=True)

        board_pixels = min(_MAX_BOARD_PIXELS, 16 * max(config.board_width, config.board_height))
        width = board_pixels + _SIDE_PANEL_WIDTH
        height = board_pixels + _TOP_BAR_HEIGHT + _STATUS_BAR_HEIGHT
        self._screen = pygame.display.set_mode((width, height))
        self._board_area = pygame.Rect(0, _TOP_BAR_HEIGHT, board_pixels, board_pixels)

        # Player 1 defaults to Basic State Machine (index 0), Player 2 to
        # Enemy State Machine (index 1) — same defaults as the Java GUI.
        self._player_pickers = [
            _ControllerPicker(pygame.Rect(10, 10, 220, 28), 0, lambda i: self._on_controller_changed(0, i)),
            _ControllerPicker(pygame.Rect(240, 10, 220, 28), 1, lambda i: self._on_controller_changed(1, i)),
        ]

        initial_controllers = self._current_selections()
        self._engine = GameEngine(config, initial_controllers)
        self._sink = _SnapshotSink()
        self._engine.add_observer(self._sink)

        self._turn_delay_millis = config.autoplay_turn_delay_millis
        self._buttons = [
            _Button(pygame.Rect(10, 46, 70, 28), "Start", self._engine.start),
            _Button(pygame.Rect(88, 46, 70, 28), "Pause", self._engine.pause),
            _Button(pygame.Rect(166, 46, 70, 28), "Step", self._engine.step),
            _Button(pygame.Rect(244, 46, 70, 28), "Reset", self._reset),
        ]
        clamped_initial_delay = max(_MIN_TURN_DELAY_MILLIS, min(_MAX_TURN_DELAY_MILLIS, self._turn_delay_millis))
        self._speed_slider = _Slider(
            pygame.Rect(404, 60, 140, 4), 0, _SPEED_SLIDER_MAX,
            _delay_to_slider(clamped_initial_delay), self._on_speed_slider_changed,
        )

        self._engine.reset(initial_controllers)

    def _current_selections(self):
        return [
            CONTROLLER_OPTIONS[picker.index].factory(seed)
            for picker, seed in zip(self._player_pickers, self._config.controller_seeds)
        ]

    def _on_controller_changed(self, player_index: int, option_index: int) -> None:
        seed = self._config.controller_seeds[player_index]
        controller = CONTROLLER_OPTIONS[option_index].factory(seed)
        self._engine.set_controller(player_index, controller)

    def _reset(self) -> None:
        self._engine.reset(self._current_selections())

    def _on_speed_slider_changed(self, slider_value: int) -> None:
        """Left is Fast (0ms), right is Slow (500ms); see _slider_to_delay
        for the curve."""
        self._turn_delay_millis = _slider_to_delay(slider_value)
        self._engine.set_turn_delay_millis(self._turn_delay_millis)

    def run(self) -> None:
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for picker in self._player_pickers:
                        picker.handle_click(event.pos)
                    for button in self._buttons:
                        button.handle_click(event.pos)
                    self._speed_slider.handle_mouse_down(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self._speed_slider.handle_mouse_motion(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._speed_slider.handle_mouse_up()

            self._draw()
            clock.tick(60)
        pygame.quit()

    def _draw(self) -> None:
        self._screen.fill(_BACKGROUND)
        for picker in self._player_pickers:
            picker.draw(self._screen, self._font)
        for button in self._buttons:
            button.draw(self._screen, self._font)
        self._draw_speed_control()

        snapshot = self._sink.latest()
        if snapshot is not None:
            draw_board(self._screen, self._board_area, snapshot)
            self._draw_side_panel(snapshot)
            self._draw_status_bar(snapshot)

        pygame.display.flip()

    def _draw_speed_control(self) -> None:
        """Controls the pause between turns during continuous play
        (Start); Step always runs immediately."""
        self._blit("Speed:", 324, 52, self._font)
        self._blit("Fast", 372, 52, self._font)
        self._speed_slider.draw(self._screen)
        self._blit("Slow", 552, 52, self._font)

    def _draw_side_panel(self, snapshot: GameSnapshot) -> None:
        x = self._board_area.right + 10
        card_height = (self._board_area.height - 10) // 2
        for i, player in enumerate(snapshot.players):
            self._draw_player_card(
                x, _TOP_BAR_HEIGHT + i * (card_height + 10), 280, card_height - 10,
                player, player.id == snapshot.active_player_id,
            )

    def _draw_player_card(self, x, y, width, height, player, active: bool) -> None:
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self._screen, (250, 250, 250), rect)
        pygame.draw.rect(self._screen, (210, 210, 210), rect, width=1)

        title = f"Player {player.id.index + 1}" + (" (active)" if active else "")
        self._blit(title, x + 8, y + 6, self._bold_font)

        swatch_color = AGENT_COLORS[player.id.index % len(AGENT_COLORS)]
        pygame.draw.rect(self._screen, swatch_color, pygame.Rect(x + 8, y + 28, 13, 13))
        self._blit(f"Score: {player.score()}", x + 28, y + 26, self._bold_font)

        lines = [
            f"Territory: {player.territory_count}",
            f"Kills: {player.kill_count}",
            f"Deaths: {player.death_count}",
            f"Turns left: {player.remaining_turns}",
            "State:",
            *self._wrap_text(player.debug_state or "", width - 16, self._font),
        ]
        for i, line in enumerate(lines):
            self._blit(line, x + 8, y + 50 + i * 18, self._font)

    @staticmethod
    def _wrap_text(text: str, max_width: int, font: pygame.font.Font) -> list[str]:
        """Greedy word-wrap so a long debug_state string doesn't run off
        the edge of its player card."""
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _draw_status_bar(self, snapshot: GameSnapshot) -> None:
        bar_y = self._board_area.bottom
        pygame.draw.rect(self._screen, _BACKGROUND, pygame.Rect(0, bar_y, self._board_area.width, _STATUS_BAR_HEIGHT))

        if snapshot.game_over:
            text = f"Game over — {self._winner_text(snapshot)}"
        else:
            active_index = self._index_of_active_player(snapshot)
            last = snapshot.last_move_result.name if snapshot.last_move_result is not None else "-"
            text = f"Active: Player {active_index + 1}   ·   Last move: {last}"
        self._blit(text, 10, bar_y + 8, self._bold_font)

        if snapshot.error_message:
            error_rect = pygame.Rect(0, bar_y + 24, self._board_area.width + _SIDE_PANEL_WIDTH, 16)
            pygame.draw.rect(self._screen, _ERROR_BG, error_rect)
            self._screen.blit(self._font.render(snapshot.error_message, True, _ERROR_TEXT), (10, bar_y + 24))

    @staticmethod
    def _index_of_active_player(snapshot: GameSnapshot) -> int:
        for i, player in enumerate(snapshot.players):
            if player.id == snapshot.active_player_id:
                return i
        return -1

    @staticmethod
    def _winner_text(snapshot: GameSnapshot) -> str:
        a, b = snapshot.players[0], snapshot.players[1]
        if a.territory_count == b.territory_count:
            return "draw"
        winner_index = 0 if a.territory_count > b.territory_count else 1
        return f"Player {winner_index + 1} wins"

    def _blit(self, text: str, x: int, y: int, font: pygame.font.Font) -> None:
        self._screen.blit(font.render(text, True, _TEXT_COLOR), (x, y))
