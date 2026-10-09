from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel


@dataclass(frozen=True)
class Board:
    """One company's job listing on one source, e.g. Board("greenhouse", "datadog")."""

    source: str  # e.g. "greenhouse"
    slug: str  # the company's id in the board URL, e.g. "datadog"

    def __str__(self) -> str:
        return f"{self.source}/{self.slug}"


class Job(BaseModel):
    """A posting from any source, normalized."""

    source: str
    source_id: str
    company: str
    title: str
    locations: list[str]
    url: str
    description: str  # plain text, no HTML
    posted_at: datetime
    updated_at: datetime | None = None  # not every source reports it
