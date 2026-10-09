"""Fetch jobs from many job sources in parallel, without one failure stopping the rest."""

import asyncio
from dataclasses import dataclass, field

import httpx
from pydantic import ValidationError

from jobfinder.http_client import HttpClient
from jobfinder.providers import PROVIDERS
from jobfinder.schema import Job, JobSource


def _failure_reason(error: Exception) -> str:
    """The error's first line, or its type when the message is empty (e.g. ReadTimeout)."""
    lines = str(error).splitlines()
    return lines[0] if lines else type(error).__name__


@dataclass
class FetchResult:
    """The outcome of fetching one job source: its jobs, or why it failed."""

    source: JobSource
    jobs: list[Job] = field(default_factory=list)
    error: str | None = None


class JobFetcher:
    """Fetches jobs from every provider through one shared HttpClient."""

    def __init__(self, http: HttpClient) -> None:
        self._providers = {name: provider(http) for name, provider in PROVIDERS.items()}

    async def fetch_source(self, source: JobSource) -> FetchResult:
        try:
            jobs = await self._providers[source.provider].fetch(source.slug)
        except (httpx.HTTPError, ValidationError) as error:
            return FetchResult(source, error=_failure_reason(error))
        return FetchResult(source, jobs=jobs)

    async def fetch_all(self, sources: list[JobSource]) -> list[FetchResult]:
        source_fetches = [self.fetch_source(source) for source in sources]
        return await asyncio.gather(*source_fetches)
