from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel


@dataclass(frozen=True)
class JobSource:
    """A company we follow on one provider, e.g. JobSource("greenhouse", "datadog")."""

    provider: str  # e.g. "greenhouse"
    slug: str  # the company's id on that provider, e.g. "datadog"

    def __str__(self) -> str:
        return f"{self.provider}/{self.slug}"


class Job(BaseModel):
    """A job from any provider, mapped to one common shape."""

    provider: str
    provider_job_id: str  # the job's id at the provider
    company: str  # display name, e.g. "Datadog"
    title: str
    locations: list[str]
    url: str
    description: str  # plain text, no HTML
    posted_at: datetime
    updated_at: datetime | None = None  # not every provider reports it


@dataclass
class JobSourceFetchResult:
    """The outcome of fetching one job source: its jobs, or why it failed."""

    source: JobSource
    jobs: list[Job] = field(default_factory=list)
    error: str | None = None
