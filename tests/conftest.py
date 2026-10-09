import os
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config

# A separate database (see docker-compose.yml), so tests never touch your real jobs.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def _migrate(database_url: str) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("DATABASE_URL", database_url)
        command.upgrade(Config(toml_file=str(PYPROJECT)), "head")


@pytest.fixture(scope="session")
def migrated_database_url() -> str:
    """Migrate once per session: it is slow, and the tables are emptied before each test."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set: copy .env.example to .env, run via `just test`")
    try:
        psycopg.connect(TEST_DATABASE_URL, connect_timeout=2).close()
    except psycopg.OperationalError:
        pytest.skip("Postgres is not running, start it with `just db-up`")
    _migrate(TEST_DATABASE_URL)
    return TEST_DATABASE_URL


@pytest.fixture
def database_url(migrated_database_url: str) -> str:
    with psycopg.connect(migrated_database_url) as connection:
        connection.execute("TRUNCATE companies, jobs")
    return migrated_database_url


@pytest.fixture
def connection(database_url: str):
    with psycopg.connect(database_url) as connection:
        yield connection
