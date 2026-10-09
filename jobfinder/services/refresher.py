"""One refresh: fetch every job source and store what was found. Entry points (the API now,
a scheduler later) only build the dependencies and present the result."""

import logging
from dataclasses import dataclass
from datetime import timedelta

from jobfinder.db.database import Database
from jobfinder.db.store import JobStore
from jobfinder.providers.fetcher import JobFetcher
from jobfinder.schema import JobSource, JobSourceFetchResult

# ponytail: fixed retention; make it a setting if someone needs closed jobs for longer.
CLOSED_JOB_RETENTION = timedelta(days=30)

logger = logging.getLogger(__name__)


@dataclass
class SourceRefresh:
    """One job source after a refresh: its fetch result and how many of its jobs are new."""

    fetch_result: JobSourceFetchResult
    new_job_count: int


def _log_refresh(source_refreshes: list[SourceRefresh]) -> None:
    """Logged, not only returned: a scheduler calling the API may discard the response."""
    for source_refresh in source_refreshes:
        if source_refresh.fetch_result.error:
            logger.warning(
                "%s failed: %s",
                source_refresh.fetch_result.source,
                source_refresh.fetch_result.error,
            )
    new_job_count = sum(source_refresh.new_job_count for source_refresh in source_refreshes)
    logger.info("refreshed %d sources, %d new jobs", len(source_refreshes), new_job_count)


class JobRefresher:
    """Fetches every job source, stores what they return, and deletes long-closed jobs."""

    def __init__(self, fetcher: JobFetcher, database: Database) -> None:
        self._fetcher = fetcher
        self._database = database

    async def _store_fetch_results(
        self, job_store: JobStore, fetch_results: list[JobSourceFetchResult]
    ) -> list[SourceRefresh]:
        # One time for the whole run: it marks which jobs are new.
        refresh_time = await job_store.database_time()
        # One after the other: they share the session's connection, which runs one query at a time.
        source_refreshes = [
            SourceRefresh(fetch_result, await job_store.save(fetch_result, refresh_time))
            for fetch_result in fetch_results
        ]
        await job_store.delete_closed_jobs(closed_before=refresh_time - CLOSED_JOB_RETENTION)
        return source_refreshes

    async def refresh(self, sources: list[JobSource]) -> list[SourceRefresh]:
        """Fetch, then store everything in one transaction, committed only once all of it is done:
        a crash halfway saves nothing. Fails with RefreshAlreadyRunningError if one is running."""
        async with self._database.refresh_session() as session:
            fetch_results = await self._fetcher.fetch_all(sources)
            source_refreshes = await self._store_fetch_results(session.jobs, fetch_results)
            await session.commit()
        _log_refresh(source_refreshes)
        return source_refreshes
