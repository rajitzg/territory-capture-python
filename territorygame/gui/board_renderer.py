"""Pure rendering: paints the full authoritative board onto a pygame
surface — territory by owner color, trails, agents, and every player's
visibility window (always shown, in that player's color — not just the
active player's). No game-rule logic. The pygame analogue of
BoardPanel.java; exact pixel layout isn't required to match, only that
the same information is visible."""

import pygame

from territorygame.engine.game_snapshot import GameSnapshot

FREE_COLOR = (235, 235, 235)
GRID_LINE_COLOR = (210, 210, 210)
TERRITORY_COLORS = [(120, 170, 235), (235, 140, 120)]
TRAIL_COLORS = [(60, 110, 190), (190, 80, 60)]
AGENT_COLORS = [(20, 60, 130), (140, 30, 20)]


def draw_board(surface: pygame.Surface, area: pygame.Rect, snapshot: GameSnapshot) -> None:
    """Draws snapshot's board into area (a sub-rectangle of surface),
    scaling cell size to fit and centering within it."""
    cell_size = max(1, min(area.width // snapshot.width, area.height // snapshot.height))
    origin_x = area.x + (area.width - cell_size * snapshot.width) // 2
    origin_y = area.y + (area.height - cell_size * snapshot.height) // 2

    _draw_cells(surface, origin_x, origin_y, cell_size, snapshot)
    _draw_agents(surface, origin_x, origin_y, cell_size, snapshot)
    _draw_visibility_windows(surface, origin_x, origin_y, cell_size, snapshot)


def _draw_cells(surface, origin_x, origin_y, cell_size, snapshot: GameSnapshot) -> None:
    for y in range(snapshot.height):
        for x in range(snapshot.width):
            cell = snapshot.cells[y][x]
            rect = pygame.Rect(origin_x + x * cell_size, origin_y + y * cell_size, cell_size, cell_size)
            pygame.draw.rect(surface, _territory_color(cell), rect)
            if cell.trail_owner is not None:
                trail_color = TRAIL_COLORS[cell.trail_owner.index % len(TRAIL_COLORS)]
                inset = max(1, cell_size // 4)
                pygame.draw.rect(
                    surface, trail_color,
                    pygame.Rect(rect.x + inset, rect.y + inset, cell_size - 2 * inset, cell_size - 2 * inset),
                )
    board_width_px = cell_size * snapshot.width
    board_height_px = cell_size * snapshot.height
    for x in range(snapshot.width + 1):
        px = origin_x + x * cell_size
        pygame.draw.line(surface, GRID_LINE_COLOR, (px, origin_y), (px, origin_y + board_height_px))
    for y in range(snapshot.height + 1):
        py = origin_y + y * cell_size
        pygame.draw.line(surface, GRID_LINE_COLOR, (origin_x, py), (origin_x + board_width_px, py))


def _territory_color(cell) -> tuple[int, int, int]:
    if cell.territory_owner is not None:
        return TERRITORY_COLORS[cell.territory_owner.index % len(TERRITORY_COLORS)]
    return FREE_COLOR


def _draw_agents(surface, origin_x, origin_y, cell_size, snapshot: GameSnapshot) -> None:
    for player in snapshot.players:
        color = AGENT_COLORS[player.id.index % len(AGENT_COLORS)]
        margin = max(1, cell_size // 6)
        rect = pygame.Rect(
            origin_x + player.position.x * cell_size + margin,
            origin_y + player.position.y * cell_size + margin,
            cell_size - 2 * margin,
            cell_size - 2 * margin,
        )
        pygame.draw.ellipse(surface, color, rect)


def _draw_visibility_windows(surface, origin_x, origin_y, cell_size, snapshot: GameSnapshot) -> None:
    for player in snapshot.players:
        color = AGENT_COLORS[player.id.index % len(AGENT_COLORS)]
        _draw_visibility_box(surface, origin_x, origin_y, cell_size, snapshot, color, player.position)


def _draw_visibility_box(surface, origin_x, origin_y, cell_size, snapshot: GameSnapshot, color, center) -> None:
    half = snapshot.visibility_window_size // 2
    min_x = max(0, center.x - half)
    min_y = max(0, center.y - half)
    max_x = min(snapshot.width - 1, center.x + half)
    max_y = min(snapshot.height - 1, center.y + half)

    rect = pygame.Rect(
        origin_x + min_x * cell_size, origin_y + min_y * cell_size,
        (max_x - min_x + 1) * cell_size, (max_y - min_y + 1) * cell_size,
    )
    pygame.draw.rect(surface, color, rect, width=2)
