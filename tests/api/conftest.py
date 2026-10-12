from collections.abc import Callable, Generator
from concurrent.futures import Executor
from pathlib import Path
from typing import Literal

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from jobfinder.db.database import Database
from jobfinder.main import create_app
from jobfinder.providers.http_client import HttpClient


@pytest.fixture
def service_token() -> str:
    return "test-service-token"


@pytest.fixture
def authorization(service_token: str) -> dict[str, str]:
    """The headers every API request needs."""
    return {"Authorization": f"Bearer {service_token}"}


@pytest.fixture
def sources_file(tmp_path: Path) -> Path:
    sources_file = tmp_path / "sources.toml"
    sources_file.write_text('greenhouse = ["datadog", "missing"]')  # the fake server 404s missing
    return sources_file


@pytest.fixture
def api_client(
    fake_http_client: Callable[[], HttpClient],
    database_url: str,
    sources_file: Path,
    service_token: str,
    parse_executor: Executor,
    anyio_backend: tuple[Literal["asyncio"], dict],
) -> Generator[TestClient]:
    app = create_app(
        Database(database_url),
        fake_http_client(),
        sources_file,
        SecretStr(service_token),
        parse_executor,
    )
    backend, backend_options = anyio_backend  # the same event loop as the async tests
    # `with` runs startup and shutdown.
    with TestClient(app, backend=backend, backend_options=backend_options) as api_client:
        yield api_client
