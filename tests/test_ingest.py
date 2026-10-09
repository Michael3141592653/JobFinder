import asyncio
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from jobfinder import ingest

GREENHOUSE_FIXTURE = Path(__file__).parent / "sources" / "fixtures" / "greenhouse.json"


def _fake_greenhouse(request: httpx.Request) -> httpx.Response:
    """datadog -> the real saved board, broken -> invalid data, anything else -> 404."""
    if "/datadog/" in request.url.path:
        return httpx.Response(200, content=GREENHOUSE_FIXTURE.read_bytes())
    if "/broken/" in request.url.path:
        return httpx.Response(200, json={"jobs": [{"id": 1}]})
    return httpx.Response(404)


def _fetch_all(boards: ingest.Boards) -> list[ingest.BoardResult]:
    async def run_against_fake_server() -> list[ingest.BoardResult]:
        transport = httpx.MockTransport(_fake_greenhouse)
        async with httpx.AsyncClient(transport=transport) as client:
            return await ingest.fetch_all(client, boards)

    return asyncio.run(run_against_fake_server())


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "boards.toml"
    path.write_text(content)
    return path


def test_load_boards_reads_sources_and_slugs(tmp_path):
    path = _write(tmp_path, 'greenhouse = ["datadog"]\nlever = ["spotify", "palantir"]\n')

    assert ingest.load_boards(path) == {"greenhouse": ["datadog"], "lever": ["spotify", "palantir"]}


def test_load_boards_rejects_unknown_source(tmp_path):
    path = _write(tmp_path, 'workday = ["acme"]\n')

    with pytest.raises(ValueError, match="workday"):
        ingest.load_boards(path)


def test_load_boards_rejects_slug_that_is_not_a_list(tmp_path):
    path = _write(tmp_path, 'greenhouse = "datadog"\n')

    with pytest.raises(ValidationError):
        ingest.load_boards(path)


def test_fetch_all_returns_jobs_for_working_board():
    [result] = _fetch_all({"greenhouse": ["datadog"]})

    assert (result.error, len(result.jobs)) == (None, 3)


@pytest.mark.parametrize(
    ("board", "expected_error"),
    [
        pytest.param("missing", "404", id="http-error"),
        pytest.param("broken", "validation error", id="invalid-data"),
    ],
)
def test_fetch_all_reports_failing_board_and_keeps_the_others(board, expected_error):
    failed, working = _fetch_all({"greenhouse": [board, "datadog"]})

    assert expected_error in failed.error
    assert failed.jobs == []
    assert len(working.jobs) == 3
