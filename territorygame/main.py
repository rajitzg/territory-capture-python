"""Application entry point."""

from territorygame.domain.game_config import GameConfig
from territorygame.gui.game_window import GameWindow


def main() -> None:
    config = GameConfig.load_default()
    GameWindow(config).run()


if __name__ == "__main__":
    main()
