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
_START_UPDATE = _load_query("start_update")


def _company_name(jobs: list[Job]) -> str | None:
    """The display name the provider gives, e.g. "Datadog"; unknown when there are no jobs."""
    return jobs[0].company if jobs else None


class JobStore:
    """Reads and writes jobs. It never commits: the DatabaseSession around it decides that."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def _save_company(
        self, source: JobSource, update_time: datetime, name: str | None, error: str | None
    ) -> int:
        params = {
            "provider": source.provider,
            "slug": source.slug,
            "name": name,
            "update_time": update_time,
            "error": error,
        }
        [company_id] = self._connection.execute(_SAVE_COMPANY, params).fetchone()
        return company_id

    def _save_jobs(self, company_id: int, jobs: list[Job], update_time: datetime) -> None:
        run_params = {"company_id": company_id, "update_time": update_time}
        params = [job.model_dump() | run_params for job in jobs]
        self._connection.cursor().executemany(_SAVE_JOB, params)

    def _close_missing_jobs(self, company_id: int, update_time: datetime) -> None:
        params = {"company_id": company_id, "update_time": update_time}
        self._connection.execute(_CLOSE_MISSING_JOBS, params)

    def _count_new_jobs(self, company_id: int, update_time: datetime) -> int:
        params = {"company_id": company_id, "update_time": update_time}
        [count] = self._connection.execute(_COUNT_NEW_JOBS, params).fetchone()
        return count

    def save(self, result: JobSourceFetchResult, update_time: datetime) -> int:
        """Store one source's fetch and return how many of its jobs are new.

        A failed fetch only records the error: its jobs stay open, since they weren't checked.
        """
        name = _company_name(result.jobs)
        company_id = self._save_company(result.source, update_time, name, result.error)
        if result.error:
            return 0
        self._save_jobs(company_id, result.jobs, update_time)
        self._close_missing_jobs(company_id, update_time)
        return self._count_new_jobs(company_id, update_time)

    def start_update(self) -> datetime:
        """Wait until no other update is storing, then return the time this update stores at.

        The time is the database's, read after the wait: a run that waited never writes an older
        time than the run before it, even when runs come from machines whose clocks differ.
        The lock is held until the session commits or rolls back.
        """
        [update_time] = self._connection.execute(_START_UPDATE).fetchone()
        return update_time

    def delete_closed_jobs(self, closed_before: datetime) -> None:
        self._connection.execute(_DELETE_CLOSED_JOBS, {"closed_before": closed_before})
