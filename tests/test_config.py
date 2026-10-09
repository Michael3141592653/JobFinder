from pathlib import Path

import pytest
from pydantic import ValidationError

from jobfinder.config import BoardsConfig
from jobfinder.schema import Board


def _write_boards_file(tmp_path: Path, content: str) -> Path:
    boards_file = tmp_path / "boards.toml"
    boards_file.write_text(content)
    return boards_file


def test_boards_config_reads_sources_and_slugs_from_toml(tmp_path):
    content = 'greenhouse = ["datadog"]\nlever = ["spotify", "palantir"]'
    boards_file = _write_boards_file(tmp_path, content)

    config = BoardsConfig.from_toml(boards_file)

    assert config.boards() == [
        Board("greenhouse", "datadog"),
        Board("lever", "spotify"),
        Board("lever", "palantir"),
    ]


def test_boards_config_rejects_unknown_source(tmp_path):
    boards_file = _write_boards_file(tmp_path, 'workday = ["acme"]\n')

    with pytest.raises(ValidationError, match="workday"):
        BoardsConfig.from_toml(boards_file)


def test_boards_config_rejects_slugs_that_are_not_a_list(tmp_path):
    boards_file = _write_boards_file(tmp_path, 'greenhouse = "datadog"\n')

    with pytest.raises(ValidationError):
        BoardsConfig.from_toml(boards_file)
