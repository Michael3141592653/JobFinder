"""Greenhouse job board API: https://developers.greenhouse.io/job-board.html"""

import html
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from jobfinder.providers.base import Provider
from jobfinder.schema import Job
from jobfinder.text import html_to_text

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


def split_locations(text: str) -> list[str]:
    """Greenhouse sends one free-text field; companies separate locations with ';' or '|'."""
    # ponytail: commas, '&' and 'or' are ambiguous ("New York, NY"), so those stay one entry
    parts = (part.strip() for part in re.split(r"[;|]", text))
    return list(dict.fromkeys(part for part in parts if part))  # dedupe, keep order


class _Location(BaseModel):
    name: str


class _GreenhouseRawJob(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int
    title: str
    absolute_url: str
    company_name: str
    location: _Location
    content: str  # HTML, entity-escaped once more on top
    first_published: datetime
    updated_at: datetime

    def to_job(self) -> Job:
        return Job(
            provider=GreenhouseProvider.name,
            provider_job_id=str(self.id),
            company=self.company_name,
            title=self.title,
            locations=split_locations(self.location.name),
            url=self.absolute_url,
            description=html_to_text(html.unescape(self.content)),
            posted_at=self.first_published,
            updated_at=self.updated_at,
        )


class _JobsResponse(BaseModel):
    jobs: list[_GreenhouseRawJob]


class GreenhouseProvider(Provider):
    name = "greenhouse"

    def jobs_url(self, slug: str) -> str:
        return f"{BASE_URL}/{slug}/jobs?content=true"  # content=true: include descriptions

    @classmethod
    def parse(cls, response_body: bytes | str, slug: str) -> list[Job]:
        raw_jobs = _JobsResponse.model_validate_json(response_body).jobs
        return [raw_job.to_job() for raw_job in raw_jobs]
