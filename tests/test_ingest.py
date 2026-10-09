import asyncio
from pathlib import Path

import httpx
import pytest
from tenacity import wait_none

from jobfinder.http_client import HttpClient
from jobfinder.ingest import BoardResult, Ingestor
from jobfinder.schema import Board

FIXTURES = Path(__file__).parent / "sources" / "fixtures"

# Exact URLs, so a wrong `board_url` in any source gets a 404 and fails the test.
RESPONSE_BODY_BY_URL = {
    "https://boards-api.greenhouse.io/v1/boards/datadog/jobs?content=true": (
        FIXTURES / "greenhouse.json"
    ).read_bytes(),
    "https://api.lever.co/v0/postings/spotify?mode=json": (FIXTURES / "lever.json").read_bytes(),
    "https://boards-api.greenhouse.io/v1/boards/broken/jobs?content=true": b'{"jobs": [{"id": 1}]}',
}


def _fake_server(request: httpx.Request) -> httpx.Response:
    response_body = RESPONSE_BODY_BY_URL.get(str(request.url))
    if response_body is None:
        return httpx.Response(404)
    return httpx.Response(200, content=response_body)


def _fetch_all(boards: list[Board]) -> list[BoardResult]:
    async def run_against_fake_server() -> list[BoardResult]:
        transport = httpx.MockTransport(_fake_server)
        async with HttpClient(transport=transport, retry_wait=wait_none()) as http:
            return await Ingestor(http).fetch_all(boards)

    return asyncio.run(run_against_fake_server())


@pytest.mark.parametrize(
    "board",
    [
        pytest.param(Board("greenhouse", "datadog"), id="greenhouse"),
        pytest.param(Board("lever", "spotify"), id="lever"),
    ],
)
def test_fetch_all_returns_jobs_for_working_board(board):
    [result] = _fetch_all([board])

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
