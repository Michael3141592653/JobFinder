import asyncio
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor

import pytest

from jobfinder.providers.fetcher import JobFetcher
from jobfinder.providers.http_client import HttpClient
from jobfinder.schema import JobSource, JobSourceFetchResult


def _fetch_all(
    fake_http_client: Callable[[], HttpClient], sources: list[JobSource]
) -> list[JobSourceFetchResult]:
    async def run_against_fake_server() -> list[JobSourceFetchResult]:
        async with fake_http_client() as http:
            return await JobFetcher(http).fetch_all(sources)

    return asyncio.run(run_against_fake_server())


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(JobSource("greenhouse", "datadog"), id="greenhouse"),
        pytest.param(JobSource("lever", "spotify"), id="lever"),
    ],
)
def test_fetch_all_returns_jobs_for_working_source(fake_http_client, source):
    [result] = _fetch_all(fake_http_client, [source])

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
    fake_http_client, slug, expected_error
):
    sources = [JobSource("greenhouse", slug), JobSource("greenhouse", "datadog")]

    failed, working = _fetch_all(fake_http_client, sources)

    assert expected_error in failed.error
    assert failed.jobs == []
    assert len(working.jobs) == 3


def test_fetch_all_parses_in_a_process_pool(fake_http_client):
    async def fetch_with_parse_processes() -> list[JobSourceFetchResult]:
        async with fake_http_client() as http:
            with ProcessPoolExecutor(max_workers=1) as parse_processes:
                job_fetcher = JobFetcher(http, parse_processes)
                return await job_fetcher.fetch_all([JobSource("greenhouse", "datadog")])

    [result] = asyncio.run(fetch_with_parse_processes())

    assert len(result.jobs) == 3  # the jobs could be sent to the process and back
