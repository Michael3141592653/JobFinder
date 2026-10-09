from datetime import datetime

from pydantic import BaseModel


class Job(BaseModel):
    """A posting from any source, normalized."""

    source: str
    source_id: str
    company: str
    title: str
    location: str
    url: str
    description: str  # plain text, no HTML
    posted_at: datetime
    updated_at: datetime | None = None  # not every source reports it
