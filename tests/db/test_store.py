from datetime import UTC, datetime, timedelta

import pytest
from psycopg.rows import dict_row

from jobfinder.db.store import JobStore
from jobfinder.schema import Job, JobSource, JobSourceFetchResult

pytestmark = pytest.mark.anyio

SOURCE = JobSource("greenhouse", "datadog")
DAY_1 = datetime(2026, 10, 1, tzinfo=UTC)
DAY_2 = DAY_1 + timedelta(days=1)
DAY_3 = DAY_1 + timedelta(days=2)


def _job(provider_job_id: str, title: str = "ML Engineer") -> Job:
    return Job(
        provider="greenhouse",
        provider_job_id=provider_job_id,
        company="Datadog",
        title=title,
        locations=["Paris, France"],
        url=f"https://example.com/jobs/{provider_job_id}",
        description="Build models.",
        posted_at=DAY_1,
    )


def _fetched(*job_ids: str) -> JobSourceFetchResult:
    return JobSourceFetchResult(SOURCE, jobs=[_job(job_id) for job_id in job_ids])


def _failed() -> JobSourceFetchResult:
    return JobSourceFetchResult(SOURCE, error="404 Not Found")


async def _job_rows(connection) -> dict[str, dict]:
    job_cursor = await connection.cursor(row_factory=dict_row).execute("SELECT * FROM jobs")
    return {row["provider_job_id"]: row for row in await job_cursor.fetchall()}


async def _company_row(connection) -> dict:
    company_cursor = await connection.cursor(row_factory=dict_row).execute(
        "SELECT * FROM companies"
    )
    return await company_cursor.fetchone()


async def test_save_counts_every_job_of_first_fetch_as_new(connection):
    new_job_count = await JobStore(connection).save(_fetched("1", "2"), DAY_1)

    assert new_job_count == 2


async def test_save_counts_only_unseen_jobs_as_new(connection):
    job_store = JobStore(connection)
    await job_store.save(_fetched("1", "2"), DAY_1)

    new_job_count = await job_store.save(_fetched("1", "2", "3"), DAY_2)

    assert new_job_count == 1


async def test_save_keeps_first_seen_at_and_moves_last_seen_at(connection):
    job_store = JobStore(connection)
    await job_store.save(_fetched("1"), DAY_1)

    await job_store.save(_fetched("1"), DAY_2)

    row = (await _job_rows(connection))["1"]
    assert (row["first_seen_at"], row["last_seen_at"]) == (DAY_1, DAY_2)


async def test_save_updates_changed_job_instead_of_duplicating_it(connection):
    job_store = JobStore(connection)
    await job_store.save(_fetched("1"), DAY_1)

    await job_store.save(
        JobSourceFetchResult(SOURCE, jobs=[_job("1", title="Senior ML Engineer")]), DAY_2
    )

    rows = await _job_rows(connection)
    assert len(rows) == 1
    assert rows["1"]["title"] == "Senior ML Engineer"


async def test_save_closes_jobs_missing_from_the_fetch(connection):
    job_store = JobStore(connection)
    await job_store.save(_fetched("1", "2"), DAY_1)

    await job_store.save(_fetched("1"), DAY_2)

    rows = await _job_rows(connection)
    assert (rows["1"]["closed_at"], rows["2"]["closed_at"]) == (None, DAY_2)


async def test_save_reopens_closed_job_that_comes_back(connection):
    job_store = JobStore(connection)
    await job_store.save(_fetched("1"), DAY_1)
    await job_store.save(_fetched(), DAY_2)

    await job_store.save(_fetched("1"), DAY_3)

    assert (await _job_rows(connection))["1"]["closed_at"] is None


async def test_save_failed_fetch_keeps_jobs_open(connection):
    job_store = JobStore(connection)
    await job_store.save(_fetched("1"), DAY_1)

    new_job_count = await job_store.save(_failed(), DAY_2)

    assert new_job_count == 0
    assert (await _job_rows(connection))["1"]["closed_at"] is None


async def test_save_failed_fetch_records_error_on_company(connection):
    await JobStore(connection).save(_failed(), DAY_1)

    company = await _company_row(connection)
    assert (company["name"], company["last_error"]) == ("datadog", "404 Not Found")


async def test_save_successful_fetch_clears_previous_error_and_sets_name(connection):
    job_store = JobStore(connection)
    await job_store.save(_failed(), DAY_1)

    await job_store.save(_fetched("1"), DAY_2)

    company = await _company_row(connection)
    assert (company["name"], company["last_error"]) == ("Datadog", None)


async def test_delete_closed_jobs_removes_only_jobs_closed_before_cutoff(connection):
    job_store = JobStore(connection)
    await job_store.save(_fetched("open", "closed-day-2", "closed-day-3"), DAY_1)
    await job_store.save(_fetched("open", "closed-day-3"), DAY_2)
    await job_store.save(_fetched("open"), DAY_3)

    await job_store.delete_closed_jobs(closed_before=DAY_3)

    assert (await _job_rows(connection)).keys() == {"open", "closed-day-3"}
