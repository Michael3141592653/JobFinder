import os
from pathlib import Path

import httpx
import psycopg
import pytest
from alembic import command
from alembic.config import Config

# A separate database (see docker-compose.yml), so tests never touch your real jobs.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"
FIXTURES = Path(__file__).parent / "providers" / "fixtures"

# Exact URLs, so a wrong `jobs_url` in any provider gets a 404 and fails the test.
RESPONSE_BODY_BY_URL = {
    "https://boards-api.greenhouse.io/v1/boards/datadog/jobs?content=true": (
        FIXTURES / "greenhouse.json"
    ).read_bytes(),
    "https://api.lever.co/v0/postings/spotify?mode=json": (FIXTURES / "lever.json").read_bytes(),
    "https://boards-api.greenhouse.io/v1/boards/broken/jobs?content=true": b'{"jobs": [{"id": 1}]}',
}


def _fake_provider_server(request: httpx.Request) -> httpx.Response:
    """Real provider responses for known URLs, a 404 otherwise, a timeout for `/timeout/`."""
    if "/timeout/" in str(request.url):
        raise httpx.ReadTimeout("", request=request)  # httpx timeouts often have no message
    response_body = RESPONSE_BODY_BY_URL.get(str(request.url))
    if response_body is None:
        return httpx.Response(404)
    return httpx.Response(200, content=response_body)


@pytest.fixture
def fake_provider_transport() -> httpx.MockTransport:
    """Pass to HttpClient(transport=...) to fetch from the fake server instead of the internet."""
    return httpx.MockTransport(_fake_provider_server)


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
