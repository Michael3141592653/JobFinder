import asyncio
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from tenacity import wait_none

from jobfinder.http import HttpClient
from jobfinder.ingest import BoardResult, BoardsConfig, Ingestor
from jobfinder.schema import Board

GREENHOUSE_FIXTURE = Path(__file__).parent / "sources" / "fixtures" / "greenhouse.json"


def _fake_greenhouse(request: httpx.Request) -> httpx.Response:
    """datadog -> the real saved board, broken -> invalid data, anything else -> 404."""
    if "/datadog/" in request.url.path:
        return httpx.Response(200, content=GREENHOUSE_FIXTURE.read_bytes())
    if "/broken/" in request.url.path:
        return httpx.Response(200, json={"jobs": [{"id": 1}]})
    return httpx.Response(404)


def _fetch_all(boards: list[Board]) -> list[BoardResult]:
    async def run_against_fake_server() -> list[BoardResult]:
        transport = httpx.MockTransport(_fake_greenhouse)
        async with HttpClient(transport=transport, retry_wait=wait_none()) as http:
            return await Ingestor(http).fetch_all(boards)

    return asyncio.run(run_against_fake_server())


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


def test_fetch_all_returns_jobs_for_working_board():
    [result] = _fetch_all([Board("greenhouse", "datadog")])

    assert (result.error, len(result.jobs)) == (None, 3)


@pytest.mark.parametrize(
    ("slug", "expected_error"),
    [
        pytest.param("missing", "404", id="http-error"),
        pytest.param("broken", "validation error", id="invalid-data"),
    ],
)
def test_fetch_all_reports_failing_board_and_keeps_the_others(slug, expected_error):
    failed, working = _fetch_all([Board("greenhouse", slug), Board("greenhouse", "datadog")])

    assert expected_error in failed.error
    assert failed.jobs == []
    assert len(working.jobs) == 3
