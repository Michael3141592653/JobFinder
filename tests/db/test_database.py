from datetime import UTC, datetime

import psycopg
import pytest

from jobfinder.db.database import Database
from jobfinder.schema import JobSource, JobSourceFetchResult

# A failed fetch is the smallest save: it writes only the company row.
FAILED_FETCH = JobSourceFetchResult(JobSource("greenhouse", "datadog"), error="404 Not Found")
NOW = datetime(2026, 10, 1, tzinfo=UTC)


def _committed_company_count(database_url: str) -> int:
    """Counted on a separate connection, which only sees committed data."""
    with psycopg.connect(database_url) as other_connection:
        [count] = other_connection.execute("SELECT COUNT(*) FROM companies").fetchone()
    return count


def test_database_session_saves_committed_work(database_url):
    with Database(database_url).session() as session:
        session.jobs.save(FAILED_FETCH, NOW)
        session.commit()

    assert _committed_company_count(database_url) == 1


def test_database_from_env_without_url_fails(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        Database.from_env()
