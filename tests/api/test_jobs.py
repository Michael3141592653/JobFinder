from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jobfinder.db.database import Database
from jobfinder.http_client import HttpClient
from jobfinder.main import create_app

SERVICE_TOKEN = "test-service-token"


@pytest.fixture
def sources_file(tmp_path: Path) -> Path:
    sources_file = tmp_path / "sources.toml"
    sources_file.write_text('greenhouse = ["datadog", "missing"]')  # the fake server 404s missing
    return sources_file


@pytest.fixture
def api_client(
    fake_http_client: Callable[[], HttpClient], database_url: str, sources_file: Path
) -> Generator[TestClient]:
    app = create_app(Database(database_url), fake_http_client(), sources_file, SERVICE_TOKEN)
    with TestClient(app) as api_client:  # `with` runs startup and shutdown
        yield api_client


def _refresh_jobs(api_client: TestClient):
    return api_client.post("/jobs/refresh", headers={"Authorization": f"Bearer {SERVICE_TOKEN}"})


def test_refresh_jobs_reports_new_jobs_per_source_and_in_total(api_client):
    response = _refresh_jobs(api_client)

    assert response.status_code == 200
    working_source, _ = response.json()["sources"]
    assert working_source == {
        "source": "greenhouse/datadog",
        "job_count": 3,
        "new_job_count": 3,
        "error": None,
    }
    assert response.json()["new_job_count"] == 3


def test_refresh_jobs_reports_the_error_of_a_failing_source(api_client):
    response = _refresh_jobs(api_client)

    _, failing_source = response.json()["sources"]
    assert failing_source["source"] == "greenhouse/missing"
    assert failing_source["error"]


def test_refresh_jobs_twice_reports_no_new_jobs(api_client):
    _refresh_jobs(api_client)

    response = _refresh_jobs(api_client)

    assert response.json()["new_job_count"] == 0


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong-token"}, {"Authorization": f"Basic {SERVICE_TOKEN}"}],
    ids=["missing", "wrong token", "not bearer"],
)
def test_refresh_jobs_without_the_right_bearer_token_is_unauthorized(api_client, headers):
    response = api_client.post("/jobs/refresh", headers=headers)

    assert response.status_code == 401


def test_refresh_jobs_while_another_refresh_runs_is_a_conflict(api_client, database_url):
    with Database(database_url).refresh_session():
        response = _refresh_jobs(api_client)

    assert response.status_code == 409
