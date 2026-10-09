"""Postgres storage: the companies we fetch and their jobs, with when each job was seen."""

from datetime import datetime

import psycopg

from jobfinder.db.sql import fetch_value, load_query
from jobfinder.schema import Job, JobSource, JobSourceFetchResult

# Loaded at import, so a missing or misnamed file fails right away, not mid-run.
_SAVE_COMPANY = load_query("save_company")
_SAVE_JOB = load_query("save_job")
_CLOSE_MISSING_JOBS = load_query("close_missing_jobs")
_COUNT_NEW_JOBS = load_query("count_new_jobs")
_DELETE_CLOSED_JOBS = load_query("delete_closed_jobs")
_DATABASE_TIME = load_query("database_time")


def _company_name(jobs: list[Job]) -> str | None:
    """The display name the provider gives, e.g. "Datadog"; unknown when there are no jobs."""
    return jobs[0].company if jobs else None


class JobStore:
    """Reads and writes jobs. It never commits: the DatabaseSession around it decides that."""

    def __init__(self, connection: psycopg.AsyncConnection) -> None:
        self._connection = connection

    async def _save_company(
        self, source: JobSource, refresh_time: datetime, company_name: str | None, error: str | None
    ) -> int:
        params = {
            "provider": source.provider,
            "slug": source.slug,
            "name": company_name,
            "refresh_time": refresh_time,
            "error": error,
        }
        return await fetch_value(self._connection, _SAVE_COMPANY, params)

    async def _save_jobs(self, company_id: int, jobs: list[Job], refresh_time: datetime) -> None:
        shared_params = {"company_id": company_id, "refresh_time": refresh_time}
        params = [job.model_dump() | shared_params for job in jobs]
        async with self._connection.cursor() as job_cursor:
            await job_cursor.executemany(_SAVE_JOB, params)

    async def _close_missing_jobs(self, company_id: int, refresh_time: datetime) -> None:
        params = {"company_id": company_id, "refresh_time": refresh_time}
        await self._connection.execute(_CLOSE_MISSING_JOBS, params)

    async def _count_new_jobs(self, company_id: int, refresh_time: datetime) -> int:
        params = {"company_id": company_id, "refresh_time": refresh_time}
        return await fetch_value(self._connection, _COUNT_NEW_JOBS, params)

    async def save(self, fetch_result: JobSourceFetchResult, refresh_time: datetime) -> int:
        """Store one source's fetch and return how many of its jobs are new.

        A failed fetch only records the error: its jobs stay open, since they weren't checked.
        """
        company_name = _company_name(fetch_result.jobs)
        company_id = await self._save_company(
            fetch_result.source, refresh_time, company_name, fetch_result.error
        )
        if fetch_result.error:
            return 0
        await self._save_jobs(company_id, fetch_result.jobs, refresh_time)
        await self._close_missing_jobs(company_id, refresh_time)
        return await self._count_new_jobs(company_id, refresh_time)

    async def database_time(self) -> datetime:
        """The database's clock, shared by every machine, unlike each machine's own clock."""
        return await fetch_value(self._connection, _DATABASE_TIME)

    async def delete_closed_jobs(self, closed_before: datetime) -> None:
        await self._connection.execute(_DELETE_CLOSED_JOBS, {"closed_before": closed_before})
