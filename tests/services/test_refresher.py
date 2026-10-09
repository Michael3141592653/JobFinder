from collections.abc import Callable
from concurrent.futures import Executor

import httpx
import pytest
from tenacity import wait_none

from jobfinder.db.database import Database, RefreshAlreadyRunningError
from jobfinder.providers.fetcher import JobFetcher
from jobfinder.providers.http_client import HttpClient
from jobfinder.schema import JobSource
from jobfinder.services.refresher import JobRefresher, SourceRefresh

pytestmark = pytest.mark.anyio

DATADOG = JobSource("greenhouse", "datadog")
SPOTIFY = JobSource("lever", "spotify")
MISSING = JobSource("greenhouse", "missing")  # the fake server answers 404


async def _refresh(
    fake_http_client: Callable[[], HttpClient],
    database_url: str,
    parse_executor: Executor,
    sources: list[JobSource],
) -> list[SourceRefresh]:
    async with fake_http_client() as http:
        job_refresher = JobRefresher(JobFetcher(http, parse_executor), Database(database_url))
        return await job_refresher.refresh(sources)


async def test_refresh_counts_every_job_of_first_run_as_new(
    fake_http_client, database_url, parse_executor
):
    source_refreshes = await _refresh(
        fake_http_client, database_url, parse_executor, [DATADOG, SPOTIFY]
    )

    assert [source_refresh.new_job_count for source_refresh in source_refreshes] == [3, 3]


async def test_refresh_counts_no_new_jobs_when_nothing_changed(
    fake_http_client, database_url, parse_executor
):
    await _refresh(fake_http_client, database_url, parse_executor, [DATADOG])

    [source_refresh] = await _refresh(fake_http_client, database_url, parse_executor, [DATADOG])

    assert source_refresh.new_job_count == 0


async def test_refresh_reports_failing_source_and_stores_the_others(
    fake_http_client, database_url, parse_executor
):
    failed, working = await _refresh(
        fake_http_client, database_url, parse_executor, [MISSING, DATADOG]
    )

    assert failed.result.error
    assert working.new_job_count == 3


async def test_refresh_while_another_refresh_runs_fails_before_fetching(
    database_url, parse_executor
):
    requests: list[httpx.Request] = []
    recording_transport = httpx.MockTransport(lambda request: requests.append(request))
    database = Database(database_url)

    async with (
        database.refresh_session(),
        HttpClient(transport=recording_transport, retry_wait=wait_none()) as http,
    ):
        with pytest.raises(RefreshAlreadyRunningError):
            await JobRefresher(JobFetcher(http, parse_executor), database).refresh([DATADOG])
    assert requests == []
