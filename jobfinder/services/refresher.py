"""One refresh: fetch every job source and store what was found. Entry points (the API now,
a scheduler later) only build the dependencies and present the result."""

from dataclasses import dataclass
from datetime import timedelta

from jobfinder.db.database import Database
from jobfinder.db.store import JobStore
from jobfinder.fetcher import JobFetcher
from jobfinder.schema import JobSource, JobSourceFetchResult

# ponytail: fixed retention; make it a setting if someone needs closed jobs for longer.
KEEP_CLOSED_JOBS = timedelta(days=30)


@dataclass
class SourceRefresh:
    """One job source after a refresh: its fetch result and how many of its jobs are new."""

    result: JobSourceFetchResult
    new_job_count: int


class JobRefresher:
    """Fetches every job source, stores the results, and deletes long-closed jobs."""

    def __init__(self, fetcher: JobFetcher, database: Database) -> None:
        self._fetcher = fetcher
        self._database = database

    async def _store_results(
        self, jobs: JobStore, results: list[JobSourceFetchResult]
    ) -> list[SourceRefresh]:
        # One time for the whole run: it marks which jobs are new.
        refresh_time = await jobs.database_time()
        # One after the other: they share the session's connection, which runs one query at a time.
        source_refreshes = [
            SourceRefresh(result, await jobs.save(result, refresh_time)) for result in results
        ]
        await jobs.delete_closed_jobs(closed_before=refresh_time - KEEP_CLOSED_JOBS)
        return source_refreshes

    async def refresh(self, sources: list[JobSource]) -> list[SourceRefresh]:
        """Fetch, then store everything in one transaction, committed only once all of it is done:
        a crash halfway saves nothing. Fails with RefreshAlreadyRunningError if one is running."""
        async with self._database.refresh_session() as session:
            results = await self._fetcher.fetch_all(sources)
            source_refreshes = await self._store_results(session.jobs, results)
            await session.commit()
        return source_refreshes
