"""One update run: fetch every job source and store what was found. Entry points (the CLI now,
the API later) only build the dependencies and present the result."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

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

    def __init__(self, fetcher: JobFetcher, store: JobStore) -> None:
        self._fetcher = fetcher
        self._store = store

    def _store_results(self, results: list[JobSourceFetchResult]) -> list[SourceUpdate]:
        seen_at = datetime.now(UTC)  # one time for the whole run: it marks which jobs are new
        updates = [SourceUpdate(result, self._store.save(result, seen_at)) for result in results]
        self._store.delete_closed_jobs(closed_before=seen_at - KEEP_CLOSED_JOBS)
        return updates

    async def update(self, sources: list[JobSource]) -> list[SourceUpdate]:
        results = await self._fetcher.fetch_all(sources)
        return self._store_results(results)
