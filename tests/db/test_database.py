from datetime import UTC, datetime

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from jobfinder.db.database import Database, RefreshAlreadyRunningError
from jobfinder.schema import JobSource, JobSourceFetchResult

pytestmark = pytest.mark.anyio

# A failed fetch is the smallest save: it writes only the company row.
FAILED_FETCH = JobSourceFetchResult(JobSource("greenhouse", "datadog"), error="404 Not Found")
REFRESH_TIME = datetime(2026, 10, 1, tzinfo=UTC)


def _committed_company_count(database_url: str) -> int:
    """Counted on a separate connection, which only sees committed data."""
    with psycopg.connect(database_url) as other_connection:
        company_count_row = other_connection.execute("SELECT COUNT(*) FROM companies").fetchone()
    assert company_count_row is not None
    return company_count_row[0]


async def _save_then_crash(database: Database) -> None:
    async with database.session() as session:
        await session.jobs.save(FAILED_FETCH, REFRESH_TIME)
        raise RuntimeError("crash before commit")


async def test_database_session_commit_saves_the_work(database_url):
    async with Database(database_url).session() as session:
        await session.jobs.save(FAILED_FETCH, REFRESH_TIME)
        await session.commit()

    assert _committed_company_count(database_url) == 1


async def test_database_session_without_commit_saves_nothing(database_url):
    async with Database(database_url).session() as session:
        await session.jobs.save(FAILED_FETCH, REFRESH_TIME)

    assert _committed_company_count(database_url) == 0


async def test_database_session_rolls_back_when_an_exception_escapes(database_url):
    with pytest.raises(RuntimeError, match="crash before commit"):
        await _save_then_crash(Database(database_url))

    assert _committed_company_count(database_url) == 0


async def test_database_check_with_missing_database_fails(database_url):
    missing_database = make_conninfo(database_url, dbname="does_not_exist")

    with pytest.raises(psycopg.OperationalError, match="does_not_exist"):
        await Database(missing_database).check_connection()


def _drop_the_refresh_lock_connection(database_url: str) -> None:
    """Ends the connection holding the refresh lock, as a Postgres restart or network drop would."""
    with psycopg.connect(database_url, autocommit=True) as other_connection:
        other_connection.execute(
            "SELECT PG_TERMINATE_BACKEND(pid) FROM pg_locks WHERE locktype = 'advisory' AND granted"
        )


async def _save_after_losing_the_refresh_lock(database_url: str) -> None:
    async with Database(database_url).refresh_session() as session:
        _drop_the_refresh_lock_connection(database_url)
        await session.jobs.save(FAILED_FETCH, REFRESH_TIME)
        await session.commit()


async def test_refresh_session_while_another_refresh_holds_it_fails(database_url):
    database = Database(database_url)

    async with database.refresh_session():
        with pytest.raises(RefreshAlreadyRunningError):
            async with database.refresh_session():
                pass


async def test_refresh_session_is_free_again_after_the_refresh(database_url):
    database = Database(database_url)
    async with database.refresh_session():
        pass

    async with database.refresh_session():
        pass  # taken again: no RefreshAlreadyRunningError


async def test_refresh_session_that_lost_its_lock_cannot_save(database_url):
    with pytest.raises(psycopg.OperationalError):
        await _save_after_losing_the_refresh_lock(database_url)

    assert _committed_company_count(database_url) == 0
