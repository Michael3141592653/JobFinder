"""Postgres storage: the companies we fetch and their jobs, with when each job was seen."""

from datetime import datetime
from pathlib import Path

import psycopg

from jobfinder.schema import Job, JobSource, JobSourceFetchResult

QUERIES = Path(__file__).parent / "queries"


def _load_query(name: str) -> str:
    return (QUERIES / f"{name}.sql").read_text(encoding="utf-8")


# Loaded at import, so a missing or misnamed file fails right away, not mid-run.
_SAVE_COMPANY = _load_query("save_company")
_SAVE_JOB = _load_query("save_job")
_CLOSE_MISSING_JOBS = _load_query("close_missing_jobs")
_COUNT_NEW_JOBS = _load_query("count_new_jobs")
_DELETE_CLOSED_JOBS = _load_query("delete_closed_jobs")
_LOCK_UPDATES = _load_query("lock_updates")


def _company_name(jobs: list[Job]) -> str | None:
    """The display name the provider gives, e.g. "Datadog"; unknown when there are no jobs."""
    return jobs[0].company if jobs else None


class JobStore:
    """Reads and writes jobs. It never commits: the DatabaseSession around it decides that."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def _save_company(
        self, source: JobSource, seen_at: datetime, name: str | None, error: str | None
    ) -> int:
        params = {
            "provider": source.provider,
            "slug": source.slug,
            "name": name,
            "seen_at": seen_at,
            "error": error,
        }
        [company_id] = self._connection.execute(_SAVE_COMPANY, params).fetchone()
        return company_id

    def _save_jobs(self, company_id: int, jobs: list[Job], seen_at: datetime) -> None:
        params = [job.model_dump() | {"company_id": company_id, "seen_at": seen_at} for job in jobs]
        self._connection.cursor().executemany(_SAVE_JOB, params)

    def _close_missing_jobs(self, company_id: int, seen_at: datetime) -> None:
        params = {"company_id": company_id, "seen_at": seen_at}
        self._connection.execute(_CLOSE_MISSING_JOBS, params)

    def _count_new_jobs(self, company_id: int, seen_at: datetime) -> int:
        params = {"company_id": company_id, "seen_at": seen_at}
        [count] = self._connection.execute(_COUNT_NEW_JOBS, params).fetchone()
        return count

    def save(self, result: JobSourceFetchResult, seen_at: datetime) -> int:
        """Store one source's fetch and return how many of its jobs are new.

        A failed fetch only records the error: its jobs stay open, since they weren't checked.
        """
        name = _company_name(result.jobs)
        company_id = self._save_company(result.source, seen_at, name, result.error)
        if result.error:
            return 0
        self._save_jobs(company_id, result.jobs, seen_at)
        self._close_missing_jobs(company_id, seen_at)
        return self._count_new_jobs(company_id, seen_at)

    def lock_updates(self) -> None:
        """Wait until no other update is storing; the lock is held until commit or rollback."""
        self._connection.execute(_LOCK_UPDATES)

    def delete_closed_jobs(self, closed_before: datetime) -> None:
        self._connection.execute(_DELETE_CLOSED_JOBS, {"closed_before": closed_before})
