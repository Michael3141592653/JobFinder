import asyncio

import httpx
from tenacity import wait_none

from jobfinder.db.store import JobStore
from jobfinder.fetcher import JobFetcher
from jobfinder.http_client import HttpClient
from jobfinder.schema import JobSource
from jobfinder.updater import JobUpdater, SourceUpdate

DATADOG = JobSource("greenhouse", "datadog")
SPOTIFY = JobSource("lever", "spotify")
MISSING = JobSource("greenhouse", "missing")  # the fake server answers 404


def _update(
    transport: httpx.MockTransport, connection, sources: list[JobSource]
) -> list[SourceUpdate]:
    async def run_against_fake_server() -> list[SourceUpdate]:
        async with HttpClient(transport=transport, retry_wait=wait_none()) as http:
            updater = JobUpdater(JobFetcher(http), JobStore(connection))
            return await updater.update(sources)

    return asyncio.run(run_against_fake_server())


def test_update_counts_every_job_of_first_run_as_new(fake_provider_transport, connection):
    updates = _update(fake_provider_transport, connection, [DATADOG, SPOTIFY])

    assert [update.new_job_count for update in updates] == [3, 3]


def test_update_counts_no_new_jobs_when_nothing_changed(fake_provider_transport, connection):
    _update(fake_provider_transport, connection, [DATADOG])

    [update] = _update(fake_provider_transport, connection, [DATADOG])

    assert update.new_job_count == 0


def test_update_reports_failing_source_and_stores_the_others(fake_provider_transport, connection):
    failed, working = _update(fake_provider_transport, connection, [MISSING, DATADOG])

    assert (failed.result.error is not None, failed.new_job_count) == (True, 0)
    assert working.new_job_count == 3
