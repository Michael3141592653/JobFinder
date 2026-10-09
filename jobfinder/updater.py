"""One update run: fetch every job source and store what was found. Entry points (the CLI now,
the API later) only build the dependencies and present the result."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from jobfinder.db.database import Database
from jobfinder.db.store import JobStore
from jobfinder.fetcher import JobFetcher
from jobfinder.schema import JobSource, JobSourceFetchResult

# ponytail: fixed retention; make it a setting if someone needs closed jobs for longer.
KEEP_CLOSED_JOBS = timedelta(days=30)


@dataclass
class SourceUpdate:
    """One job source after an update: its fetch result and how many of its jobs are new."""

    result: JobSourceFetchResult
    new_job_count: int


class JobUpdater:
    """Fetches every job source, stores the results, and deletes long-closed jobs."""

    def __init__(self, fetcher: JobFetcher, database: Database) -> None:
        self._fetcher = fetcher
        self._database = database

    def _store_results(
        self, jobs: JobStore, results: list[JobSourceFetchResult]
    ) -> list[SourceUpdate]:
        seen_at = datetime.now(UTC)  # one time for the whole run: it marks which jobs are new
        updates = [SourceUpdate(result, jobs.save(result, seen_at)) for result in results]
        jobs.delete_closed_jobs(closed_before=seen_at - KEEP_CLOSED_JOBS)
        return updates

    async def update(self, sources: list[JobSource]) -> list[SourceUpdate]:
        """Fetch, then store everything in one transaction, committed only once all of it is done:
        a crash halfway saves nothing."""
        # Connect before fetching: a stopped Postgres fails before the slow part.
        with self._database.session() as session:
            results = await self._fetcher.fetch_all(sources)
            session.jobs.lock_updates()
            # seen_at is taken after the lock, so a run that waited never writes an older time.
            updates = self._store_results(session.jobs, results)
            session.commit()
        return updates
