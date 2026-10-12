from collections.abc import Generator
from contextlib import contextmanager

import psycopg
import pytest
from fastapi.testclient import TestClient

from jobfinder.db.sql import load_query


def _refresh_jobs(api_client: TestClient, authorization: dict[str, str]):
    return api_client.post("/jobs/refresh", headers=authorization)


def test_refresh_jobs_reports_new_jobs_per_source_and_in_total(api_client, authorization):
    response = _refresh_jobs(api_client, authorization)

    assert response.status_code == 200
    working_source, _ = response.json()["sources"]
    assert working_source == {
        "source": "greenhouse/datadog",
        "job_count": 3,
        "new_job_count": 3,
        "error": None,
    }
    assert response.json()["new_job_count"] == 3


def test_refresh_jobs_reports_the_error_of_a_failing_source(api_client, authorization):
    response = _refresh_jobs(api_client, authorization)

    _, failing_source = response.json()["sources"]
    assert failing_source["source"] == "greenhouse/missing"
    assert failing_source["error"]


def test_refresh_jobs_twice_reports_no_new_jobs(api_client, authorization):
    _refresh_jobs(api_client, authorization)

    response = _refresh_jobs(api_client, authorization)

    assert response.json()["new_job_count"] == 0


@pytest.mark.parametrize(
    "headers_with",
    [
        pytest.param(lambda service_token: {}, id="missing"),
        pytest.param(lambda service_token: {"Authorization": "Bearer wrong"}, id="wrong token"),
        pytest.param(
            lambda service_token: {"Authorization": f"Basic {service_token}"}, id="not bearer"
        ),
    ],
)
def test_refresh_jobs_without_the_right_bearer_token_is_unauthorized(
    api_client, service_token, headers_with
):
    response = api_client.post("/jobs/refresh", headers=headers_with(service_token))

    assert response.status_code == 401


@contextmanager
def _another_refresh_running(database_url: str) -> Generator[None]:
    """Holds the refresh lock on its own connection, as a running refresh would."""
    with psycopg.connect(database_url, autocommit=True) as lock_connection:
        lock_connection.execute(load_query("try_lock_refreshes"))
        yield


def test_refresh_jobs_while_another_refresh_runs_is_a_conflict(
    api_client, authorization, database_url
):
    with _another_refresh_running(database_url):
        response = _refresh_jobs(api_client, authorization)

    assert response.status_code == 409
