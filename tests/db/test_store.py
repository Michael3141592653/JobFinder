import threading
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row

from jobfinder.db.session import DatabaseSession
from jobfinder.db.store import JobStore
from jobfinder.schema import Job, JobSource, JobSourceFetchResult

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


def _job_rows(connection) -> dict[str, dict]:
    rows = connection.cursor(row_factory=dict_row).execute("SELECT * FROM jobs").fetchall()
    return {row["provider_job_id"]: row for row in rows}


def _company_row(connection) -> dict:
    return connection.cursor(row_factory=dict_row).execute("SELECT * FROM companies").fetchone()


def _lock_updates_and_commit(connection: psycopg.Connection) -> None:
    with DatabaseSession(connection) as session:
        session.jobs.lock_updates()
        session.commit()


def test_save_counts_every_job_of_first_fetch_as_new(connection):
    new_job_count = JobStore(connection).save(_fetched("1", "2"), DAY_1)

    assert new_job_count == 2


def test_save_counts_only_unseen_jobs_as_new(connection):
    store = JobStore(connection)
    store.save(_fetched("1", "2"), DAY_1)

    new_job_count = store.save(_fetched("1", "2", "3"), DAY_2)

    assert new_job_count == 1


def test_save_keeps_first_seen_and_moves_last_seen(connection):
    store = JobStore(connection)
    store.save(_fetched("1"), DAY_1)

    store.save(_fetched("1"), DAY_2)

    row = _job_rows(connection)["1"]
    assert (row["first_seen"], row["last_seen"]) == (DAY_1, DAY_2)


def test_save_updates_changed_job_instead_of_duplicating_it(connection):
    store = JobStore(connection)
    store.save(_fetched("1"), DAY_1)

    store.save(JobSourceFetchResult(SOURCE, jobs=[_job("1", title="Senior ML Engineer")]), DAY_2)

    rows = _job_rows(connection)
    assert len(rows) == 1
    assert rows["1"]["title"] == "Senior ML Engineer"


def test_save_closes_jobs_missing_from_the_fetch(connection):
    store = JobStore(connection)
    store.save(_fetched("1", "2"), DAY_1)

    store.save(_fetched("1"), DAY_2)

    rows = _job_rows(connection)
    assert (rows["1"]["closed_at"], rows["2"]["closed_at"]) == (None, DAY_2)


def test_save_reopens_closed_job_that_comes_back(connection):
    store = JobStore(connection)
    store.save(_fetched("1"), DAY_1)
    store.save(_fetched(), DAY_2)

    store.save(_fetched("1"), DAY_3)

    assert _job_rows(connection)["1"]["closed_at"] is None


def test_save_failed_fetch_keeps_jobs_open(connection):
    store = JobStore(connection)
    store.save(_fetched("1"), DAY_1)

    new_job_count = store.save(_failed(), DAY_2)

    assert new_job_count == 0
    assert _job_rows(connection)["1"]["closed_at"] is None


def test_save_failed_fetch_records_error_on_company(connection):
    JobStore(connection).save(_failed(), DAY_1)

    company = _company_row(connection)
    assert (company["name"], company["last_error"]) == ("datadog", "404 Not Found")


def test_save_successful_fetch_clears_previous_error_and_sets_name(connection):
    store = JobStore(connection)
    store.save(_failed(), DAY_1)

    store.save(_fetched("1"), DAY_2)

    company = _company_row(connection)
    assert (company["name"], company["last_error"]) == ("Datadog", None)


def test_delete_closed_jobs_removes_only_jobs_closed_before_cutoff(connection):
    store = JobStore(connection)
    store.save(_fetched("open", "closed-day-2", "closed-day-3"), DAY_1)
    store.save(_fetched("open", "closed-day-3"), DAY_2)
    store.save(_fetched("open"), DAY_3)

    store.delete_closed_jobs(closed_before=DAY_3)

    assert _job_rows(connection).keys() == {"open", "closed-day-3"}


def test_lock_updates_makes_second_update_wait_until_first_commits(database_url):
    with psycopg.connect(database_url) as first, psycopg.connect(database_url) as second:
        with DatabaseSession(first) as first_session:
            first_session.jobs.lock_updates()
            second_update = threading.Thread(target=_lock_updates_and_commit, args=[second])
            second_update.start()
            second_update.join(timeout=0.5)
            assert second_update.is_alive()  # still waiting for the first update's lock
            first_session.commit()

        second_update.join(timeout=5)
        assert not second_update.is_alive()
