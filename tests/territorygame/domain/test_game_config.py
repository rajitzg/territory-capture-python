import pytest

from territorygame.api.grid_position import GridPosition
from territorygame.domain.game_config import GameConfig


def _valid_config_with(
    board_width, board_height, visibility_window_size, turns_per_player,
    respawn_positions, starting_territory_size, autoplay_turn_delay_millis,
    max_attempts_per_turn,
):
    return GameConfig(
        board_width, board_height, visibility_window_size, turns_per_player,
        respawn_positions, starting_territory_size, autoplay_turn_delay_millis,
        max_attempts_per_turn, [1, 2],
    )


def test_rejects_non_positive_board_dimensions():
    with pytest.raises(ValueError):
        _valid_config_with(0, 10, 5, 10, [GridPosition(1, 1), GridPosition(8, 8)], 1, 0, 20)


def test_rejects_even_visibility_window_size():
    with pytest.raises(ValueError):
        _valid_config_with(10, 10, 4, 10, [GridPosition(1, 1), GridPosition(8, 8)], 1, 0, 20)


def test_rejects_visibility_window_larger_than_the_board():
    with pytest.raises(ValueError):
        _valid_config_with(10, 10, 11, 10, [GridPosition(1, 1), GridPosition(8, 8)], 1, 0, 20)


def test_rejects_non_positive_turns_per_player():
    with pytest.raises(ValueError):
        _valid_config_with(10, 10, 5, 0, [GridPosition(1, 1), GridPosition(8, 8)], 1, 0, 20)


def test_rejects_non_positive_starting_territory_size():
    with pytest.raises(ValueError):
        _valid_config_with(10, 10, 5, 10, [GridPosition(1, 1), GridPosition(8, 8)], 0, 0, 20)


def test_rejects_negative_auto_play_delay():
    with pytest.raises(ValueError):
        _valid_config_with(10, 10, 5, 10, [GridPosition(1, 1), GridPosition(8, 8)], 1, -1, 20)


def test_rejects_non_positive_max_attempts_per_turn():
    with pytest.raises(ValueError):
        _valid_config_with(10, 10, 5, 10, [GridPosition(1, 1), GridPosition(8, 8)], 1, 0, 0)


def test_rejects_out_of_bounds_respawn_position():
    with pytest.raises(ValueError):
        _valid_config_with(10, 10, 5, 10, [GridPosition(1, 1), GridPosition(20, 20)], 1, 0, 20)


def test_rejects_overlapping_starting_territories():
    with pytest.raises(ValueError):
        _valid_config_with(10, 10, 5, 10, [GridPosition(4, 4), GridPosition(5, 5)], 3, 0, 20)


def test_rejects_controller_seed_count_mismatch():
    with pytest.raises(ValueError):
        GameConfig(10, 10, 5, 10, [GridPosition(1, 1), GridPosition(8, 8)], 1, 0, 20, [1])


def test_accepts_a_well_formed_config():
    _valid_config_with(10, 10, 5, 10, [GridPosition(1, 1), GridPosition(8, 8)], 1, 0, 20)
    # No exception is the assertion.


def test_load_default_reads_the_packaged_resource_file():
    config = GameConfig.load_default()

    assert config.board_width == 50
    assert config.board_height == 50
    assert config.visibility_window_size == 11
    assert config.turns_per_player == 2000
    assert config.respawn_positions == [GridPosition(4, 25), GridPosition(45, 25)]
    assert config.controller_seeds == [1001, 2002]
