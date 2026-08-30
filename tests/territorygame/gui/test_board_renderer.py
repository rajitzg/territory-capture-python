import pygame

from territorygame.api.grid_position import GridPosition
from territorygame.domain.player_id import PlayerId
from territorygame.engine.game_snapshot import CellSnapshot, GameSnapshot, PlayerSnapshot
from territorygame.gui.board_renderer import draw_board


def _snapshot() -> GameSnapshot:
    player0 = PlayerId(0)
    cells = tuple(
        tuple(CellSnapshot(player0 if x == 0 and y == 0 else None, None) for x in range(4)) for y in range(4)
    )
    players = (PlayerSnapshot(player0, GridPosition(1, 1), 1, 0, 0, 10, (), None),)
    return GameSnapshot(4, 4, cells, players, player0, None, 3, False, None)


def test_draw_board_paints_something_onto_the_surface():
    pygame.init()
    surface = pygame.Surface((200, 200))
    surface.fill((255, 255, 255))

    draw_board(surface, surface.get_rect(), _snapshot())

    # At least one sampled pixel differs from the untouched white
    # background, confirming something was actually painted.
    colors = {surface.get_at((x, y))[:3] for x in range(0, 200, 10) for y in range(0, 200, 10)}
    assert colors != {(255, 255, 255)}
    pygame.quit()
