import asyncio
from collections.abc import Callable

from jobfinder.db.database import Database
from jobfinder.fetcher import JobFetcher
from jobfinder.http_client import HttpClient
from jobfinder.schema import JobSource
from jobfinder.updater import JobUpdater, SourceUpdate

DATADOG = JobSource("greenhouse", "datadog")
SPOTIFY = JobSource("lever", "spotify")
MISSING = JobSource("greenhouse", "missing")  # the fake server answers 404


def _update(
    fake_http_client: Callable[[], HttpClient], database_url: str, sources: list[JobSource]
) -> list[SourceUpdate]:
    async def run_against_fake_server() -> list[SourceUpdate]:
        async with fake_http_client() as http:
            updater = JobUpdater(JobFetcher(http), Database(database_url))
            return await updater.update(sources)

    return asyncio.run(run_against_fake_server())


def test_update_counts_every_job_of_first_run_as_new(fake_http_client, database_url):
    updates = _update(fake_http_client, database_url, [DATADOG, SPOTIFY])

    assert [update.new_job_count for update in updates] == [3, 3]


def test_update_counts_no_new_jobs_when_nothing_changed(fake_http_client, database_url):
    _update(fake_http_client, database_url, [DATADOG])

    [update] = _update(fake_http_client, database_url, [DATADOG])

    assert update.new_job_count == 0


def test_update_reports_failing_source_and_stores_the_others(fake_http_client, database_url):
    failed, working = _update(fake_http_client, database_url, [MISSING, DATADOG])

    assert failed.result.error
    assert working.new_job_count == 3
