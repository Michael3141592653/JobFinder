"""Greenhouse job board API: https://developers.greenhouse.io/job-board.html"""

import html
from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict

from jobfinder.schema import Job
from jobfinder.text import html_to_text

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


class _Location(BaseModel):
    name: str


class GreenhouseJob(BaseModel):
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
            source="greenhouse",
            source_id=str(self.id),
            company=self.company_name,
            title=self.title,
            location=self.location.name,
            url=self.absolute_url,
            description=html_to_text(html.unescape(self.content)),
            posted_at=self.first_published,
            updated_at=self.updated_at,
        )


class _Board(BaseModel):
    jobs: list[GreenhouseJob]


def parse(raw: bytes | str) -> list[Job]:
    return [job.to_job() for job in _Board.model_validate_json(raw).jobs]


async def fetch(client: httpx.AsyncClient, board: str) -> list[Job]:
    response = await client.get(f"{BASE_URL}/{board}/jobs", params={"content": "true"})
    response.raise_for_status()
    return parse(response.content)
