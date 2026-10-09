"""Lever postings API: https://github.com/lever/postings-api"""

import html
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic.alias_generators import to_camel

from jobfinder.schema import Job
from jobfinder.sources.base import Source
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


class _LeverRawJob(BaseModel):
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
            source=LeverSource.name,
            source_id=self.id,
            company=company,
            title=self.title,
            locations=self.categories.all_locations,
            url=self.hosted_url,
            description=html_to_text(self._full_description_html()),
            posted_at=self.created_at,
        )


_BoardResponse = TypeAdapter(list[_LeverRawJob])


class LeverSource(Source):
    name = "lever"

    def board_url(self, slug: str) -> str:
        return f"{BASE_URL}/{slug}?mode=json"

    @classmethod
    def parse(cls, response_body: bytes | str, slug: str) -> list[Job]:
        """Lever doesn't return the company name, so the board slug stands in for it."""
        raw_jobs = _BoardResponse.validate_json(response_body)
        return [raw_job.to_job(company=slug) for raw_job in raw_jobs]
