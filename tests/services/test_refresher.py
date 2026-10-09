import asyncio
from collections.abc import Callable

import httpx
import pytest
from tenacity import wait_none

from jobfinder.db.database import Database, RefreshAlreadyRunningError
from jobfinder.fetcher import JobFetcher
from jobfinder.http_client import HttpClient
from jobfinder.schema import JobSource
from jobfinder.services.refresher import JobRefresher, SourceRefresh

DATADOG = JobSource("greenhouse", "datadog")
SPOTIFY = JobSource("lever", "spotify")
MISSING = JobSource("greenhouse", "missing")  # the fake server answers 404


def _refresh(
    fake_http_client: Callable[[], HttpClient], database_url: str, sources: list[JobSource]
) -> list[SourceRefresh]:
    async def run_against_fake_server() -> list[SourceRefresh]:
        async with fake_http_client() as http:
            job_refresher = JobRefresher(JobFetcher(http), Database(database_url))
            return await job_refresher.refresh(sources)

    return asyncio.run(run_against_fake_server())


def test_refresh_counts_every_job_of_first_run_as_new(fake_http_client, database_url):
    source_refreshes = _refresh(fake_http_client, database_url, [DATADOG, SPOTIFY])

    assert [source_refresh.new_job_count for source_refresh in source_refreshes] == [3, 3]


def test_refresh_counts_no_new_jobs_when_nothing_changed(fake_http_client, database_url):
    _refresh(fake_http_client, database_url, [DATADOG])

    [source_refresh] = _refresh(fake_http_client, database_url, [DATADOG])

    assert source_refresh.new_job_count == 0


def test_refresh_reports_failing_source_and_stores_the_others(fake_http_client, database_url):
    failed, working = _refresh(fake_http_client, database_url, [MISSING, DATADOG])

    assert failed.result.error
    assert working.new_job_count == 3


def test_refresh_while_another_refresh_runs_fails_before_fetching(database_url):
    requests: list[httpx.Request] = []
    recording_transport = httpx.MockTransport(lambda request: requests.append(request))
    database = Database(database_url)

    async def refresh_while_another_runs() -> None:
        async with HttpClient(transport=recording_transport, retry_wait=wait_none()) as http:
            await JobRefresher(JobFetcher(http), database).refresh([DATADOG])

    with database.refresh_session(), pytest.raises(RefreshAlreadyRunningError):
        asyncio.run(refresh_while_another_runs())
    assert requests == []
