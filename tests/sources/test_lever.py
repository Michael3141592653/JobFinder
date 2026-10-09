from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from jobfinder.schema import Job
from jobfinder.sources import lever

# Real Spotify board response, trimmed to 3 jobs (one with no `additional` section).
FIXTURE = Path(__file__).parent / "fixtures" / "lever.json"


@pytest.fixture
def jobs() -> list[Job]:
    return lever.parse(FIXTURE.read_bytes(), company="spotify")


def test_parse_returns_every_job_on_the_board(jobs):
    assert len(jobs) == 3


def test_parse_maps_lever_fields_to_job(jobs):
    job = jobs[0]

    assert job.model_dump(include={"source", "source_id", "title", "location", "url"}) == {
        "source": "lever",
        "source_id": "2193db3f-77c5-43b8-b030-8f92c9882bf1",
        "title": "Android Engineer - Experience",
        "location": "London",
        "url": "https://jobs.lever.co/spotify/2193db3f-77c5-43b8-b030-8f92c9882bf1",
    }


def test_parse_uses_given_company_name(jobs):
    assert {job.company for job in jobs} == {"spotify"}


def test_parse_converts_millisecond_timestamp_to_utc_date(jobs):
    assert jobs[0].posted_at == datetime(2026, 6, 23, 11, 29, 45, 805000, tzinfo=UTC)


def test_parse_leaves_updated_at_empty(jobs):
    assert all(job.updated_at is None for job in jobs)


def test_parse_includes_list_sections_in_description(jobs):
    assert "What You'll Do" in jobs[0].description


@pytest.mark.parametrize("markup", ["<li>", "<div>", "&nbsp;", "&rsquo;"])
def test_parse_leaves_no_html_in_description(jobs, markup):
    assert not any(markup in job.description for job in jobs)


def test_parse_rejects_job_missing_required_fields():
    raw = '[{"id": "abc", "text": "ML Engineer"}]'

    with pytest.raises(ValidationError):
        lever.parse(raw, company="spotify")
