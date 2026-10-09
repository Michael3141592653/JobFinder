from collections.abc import Callable
from concurrent.futures import Executor, ProcessPoolExecutor

import pytest

from jobfinder.providers.fetcher import JobFetcher
from jobfinder.providers.http_client import HttpClient
from jobfinder.schema import JobSource, JobSourceFetchResult

pytestmark = pytest.mark.anyio


async def _fetch_all(
    fake_http_client: Callable[[], HttpClient],
    parse_executor: Executor,
    sources: list[JobSource],
) -> list[JobSourceFetchResult]:
    async with fake_http_client() as http:
        return await JobFetcher(http, parse_executor).fetch_all(sources)


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(JobSource("greenhouse", "datadog"), id="greenhouse"),
        pytest.param(JobSource("lever", "spotify"), id="lever"),
    ],
)
async def test_fetch_all_returns_jobs_for_working_source(fake_http_client, parse_executor, source):
    [result] = await _fetch_all(fake_http_client, parse_executor, [source])

    assert (result.error, len(result.jobs)) == (None, 3)


@pytest.mark.parametrize(
    ("slug", "expected_error"),
    [
        pytest.param("missing", "404", id="http-error"),
        pytest.param("broken", "validation error", id="invalid-data"),
        pytest.param("timeout", "ReadTimeout", id="error-without-message"),
    ],
)
async def test_fetch_all_reports_failing_source_and_keeps_the_others(
    fake_http_client, parse_executor, slug, expected_error
):
    sources = [JobSource("greenhouse", slug), JobSource("greenhouse", "datadog")]

    failed, working = await _fetch_all(fake_http_client, parse_executor, sources)

    assert expected_error in failed.error
    assert failed.jobs == []
    assert len(working.jobs) == 3


async def test_fetch_all_parses_in_a_process_pool(fake_http_client):
    with ProcessPoolExecutor(max_workers=1) as parse_processes:
        sources = [JobSource("greenhouse", "datadog")]

        [result] = await _fetch_all(fake_http_client, parse_processes, sources)

    assert len(result.jobs) == 3  # the jobs could be sent to the process and back
