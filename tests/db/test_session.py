from datetime import UTC, datetime

import psycopg
import pytest

from jobfinder.db.session import DatabaseSession
from jobfinder.schema import JobSource, JobSourceFetchResult

# A failed fetch is the smallest save: it writes only the company row.
FAILED_FETCH = JobSourceFetchResult(JobSource("greenhouse", "datadog"), error="404 Not Found")
NOW = datetime(2026, 10, 1, tzinfo=UTC)


def _committed_company_count(database_url: str) -> int:
    """Counted on a separate connection, which only sees committed data."""
    with psycopg.connect(database_url) as other_connection:
        [count] = other_connection.execute("SELECT COUNT(*) FROM companies").fetchone()
    return count


def _save_then_crash(connection: psycopg.Connection) -> None:
    with DatabaseSession(connection) as session:
        session.jobs.save(FAILED_FETCH, NOW)
        raise RuntimeError("crash before commit")


def test_session_commit_saves_the_work(connection, database_url):
    with DatabaseSession(connection) as session:
        session.jobs.save(FAILED_FETCH, NOW)
        session.commit()

    assert _committed_company_count(database_url) == 1


def test_session_without_commit_saves_nothing(connection, database_url):
    with DatabaseSession(connection) as session:
        session.jobs.save(FAILED_FETCH, NOW)

    assert _committed_company_count(database_url) == 0


def test_session_rolls_back_when_an_exception_escapes(connection, database_url):
    with pytest.raises(RuntimeError, match="crash before commit"):
        _save_then_crash(connection)

    assert _committed_company_count(database_url) == 0
