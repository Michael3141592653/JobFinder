import asyncio

import httpx
import pytest
from tenacity import wait_none

from jobfinder.fetcher import JobFetcher
from jobfinder.http_client import HttpClient
from jobfinder.schema import JobSource, JobSourceFetchResult


def _fetch_all(
    transport: httpx.MockTransport, sources: list[JobSource]
) -> list[JobSourceFetchResult]:
    async def run_against_fake_server() -> list[JobSourceFetchResult]:
        async with HttpClient(transport=transport, retry_wait=wait_none()) as http:
            return await JobFetcher(http).fetch_all(sources)

    return asyncio.run(run_against_fake_server())


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(JobSource("greenhouse", "datadog"), id="greenhouse"),
        pytest.param(JobSource("lever", "spotify"), id="lever"),
    ],
)
def test_fetch_all_returns_jobs_for_working_source(fake_provider_transport, source):
    [result] = _fetch_all(fake_provider_transport, [source])

    assert (result.error, len(result.jobs)) == (None, 3)


@pytest.mark.parametrize(
    ("slug", "expected_error"),
    [
        pytest.param("missing", "404", id="http-error"),
        pytest.param("broken", "validation error", id="invalid-data"),
        pytest.param("timeout", "ReadTimeout", id="error-without-message"),
    ],
)
def test_fetch_all_reports_failing_source_and_keeps_the_others(
    fake_provider_transport, slug, expected_error
):
    sources = [JobSource("greenhouse", slug), JobSource("greenhouse", "datadog")]

    failed, working = _fetch_all(fake_provider_transport, sources)

    assert expected_error in failed.error
    assert failed.jobs == []
    assert len(working.jobs) == 3
