from pathlib import Path

import pytest
from pydantic import ValidationError

from jobfinder.providers.greenhouse import GreenhouseProvider, split_locations
from jobfinder.schema import Job

# Real Datadog response, trimmed to 3 jobs (US, Italy remote, Japan).
FIXTURE = Path(__file__).parent / "fixtures" / "greenhouse.json"


@pytest.fixture
def jobs() -> list[Job]:
    return GreenhouseProvider.parse(FIXTURE.read_bytes(), slug="datadog")


def test_parse_returns_every_job_in_the_response(jobs):
    assert len(jobs) == 3


def test_parse_maps_greenhouse_fields_to_job(jobs):
    expected = {
        "provider": "greenhouse",
        "provider_job_id": "8204056",
        "company": "Datadog",
        "locations": ["Italy, Remote", "Spain, Remote"],
        "url": "https://careers.datadoghq.com/detail/8204056/?gh_jid=8204056",
    }

    assert jobs[1].model_dump(include=expected.keys()) == expected


def test_parse_strips_whitespace_around_title(jobs):
    assert jobs[1].title == "Partner Solutions Architect (EMEA)"


def test_parse_keeps_timezone_on_dates(jobs):
    assert all(job.posted_at.tzinfo and job.updated_at.tzinfo for job in jobs)


@pytest.mark.parametrize("markup", ["<p>", "&lt;", "&amp;", "&nbsp;"])
def test_parse_leaves_no_html_in_description(jobs, markup):
    assert not any(markup in job.description for job in jobs)


def test_parse_rejects_job_missing_required_fields():
    response_body = '{"jobs": [{"id": 1, "title": "ML Engineer"}]}'

    with pytest.raises(ValidationError):
        GreenhouseProvider.parse(response_body, slug="datadog")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("Tokyo, Japan", ["Tokyo, Japan"], id="single"),
        pytest.param("Amsterdam, NL; Dublin, IE", ["Amsterdam, NL", "Dublin, IE"], id="semicolon"),
        pytest.param("SF, CA | NYC, NY", ["SF, CA", "NYC, NY"], id="pipe"),
        pytest.param("NYC, NY; SF, CA | NYC, NY", ["NYC, NY", "SF, CA"], id="drops-duplicates"),
        pytest.param("London, Dublin", ["London, Dublin"], id="commas-not-split"),
    ],
)
def test_split_locations(text, expected):
    assert split_locations(text) == expected
