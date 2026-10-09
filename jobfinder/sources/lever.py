"""Lever postings API: https://github.com/lever/postings-api"""

import html
from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic.alias_generators import to_camel

from jobfinder.schema import Job
from jobfinder.text import html_to_text

BASE_URL = "https://api.lever.co/v0/postings"


class _Categories(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)

    all_locations: list[str]


class _Section(BaseModel):
    heading: str = Field(alias="text")  # e.g. "What You'll Do"
    content: str  # HTML list items


def _section_html(section: _Section) -> str:
    return f"<h3>{html.escape(section.heading)}</h3><ul>{section.content}</ul>"


class LeverJob(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, str_strip_whitespace=True)

    id: str
    title: str = Field(alias="text")
    hosted_url: str
    categories: _Categories
    created_at: datetime  # sent as milliseconds since epoch
    description: str  # HTML intro; the rest is in `lists` and `additional`
    lists: list[_Section]
    additional: str

    def _full_description_html(self) -> str:
        sections = "".join(_section_html(section) for section in self.lists)
        return self.description + sections + self.additional

    def to_job(self, company: str) -> Job:
        return Job(
            source="lever",
            source_id=self.id,
            company=company,
            title=self.title,
            locations=self.categories.all_locations,
            url=self.hosted_url,
            description=html_to_text(self._full_description_html()),
            posted_at=self.created_at,
        )


_Board = TypeAdapter(list[LeverJob])


def parse(raw: bytes | str, company: str) -> list[Job]:
    """Lever doesn't return the company name, so the caller passes it in."""
    return [job.to_job(company) for job in _Board.validate_json(raw)]


async def fetch(client: httpx.AsyncClient, board: str) -> list[Job]:
    response = await client.get(f"{BASE_URL}/{board}", params={"mode": "json"})
    response.raise_for_status()
    return parse(response.content, company=board)
