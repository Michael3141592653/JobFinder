import asyncio

import httpx
import pytest
from tenacity import wait_none

from jobfinder import http

# Same retry rules, without the real waits between attempts.
get_without_waiting = http.get.retry_with(wait=wait_none())


def _replay(outcomes: list[int | Exception], requests: list[httpx.Request]) -> httpx.MockTransport:
    """A fake server answering each request with the next status code or network error."""
    pending = iter(outcomes)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        outcome = next(pending)
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome, content=b"body")

    return httpx.MockTransport(handler)


def _get(outcomes: list[int | Exception], requests: list[httpx.Request]) -> bytes:
    async def run_against_fake_server() -> bytes:
        async with httpx.AsyncClient(transport=_replay(outcomes, requests)) as client:
            return await get_without_waiting(client, "https://example.com")

    return asyncio.run(run_against_fake_server())


def test_get_returns_body_on_success():
    assert _get([200], []) == b"body"


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(429, id="rate-limited"),
        pytest.param(500, id="server-error"),
        pytest.param(503, id="unavailable"),
        pytest.param(httpx.ConnectError("refused"), id="network-error"),
    ],
)
def test_get_retries_temporary_failure_then_succeeds(failure):
    requests = []

    body = _get([failure, 200], requests)

    assert (body, len(requests)) == (b"body", 2)


def test_get_does_not_retry_client_error():
    requests = []

    with pytest.raises(httpx.HTTPStatusError):
        _get([404], requests)

    assert len(requests) == 1


def test_get_gives_up_after_three_attempts():
    requests = []

    with pytest.raises(httpx.HTTPStatusError):
        _get([503, 503, 503], requests)

    assert len(requests) == 3
