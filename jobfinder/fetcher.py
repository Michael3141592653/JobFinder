"""Fetch jobs from many job sources in parallel, without one failure stopping the rest."""

import asyncio

import httpx
from pydantic import ValidationError

from jobfinder.http_client import HttpClient
from jobfinder.providers import PROVIDERS
from jobfinder.schema import JobSource, JobSourceFetchResult


def _failure_reason(error: Exception) -> str:
    """The error's first line, or its type when the message is empty (e.g. ReadTimeout)."""
    lines = str(error).splitlines()
    return lines[0] if lines else type(error).__name__


class JobFetcher:
    """Fetches jobs from every provider through one shared HttpClient."""

    def __init__(self, http: HttpClient) -> None:
        self._providers = {name: provider(http) for name, provider in PROVIDERS.items()}

    async def fetch_source(self, source: JobSource) -> JobSourceFetchResult:
        try:
            jobs = await self._providers[source.provider].fetch(source.slug)
        except (httpx.HTTPError, ValidationError) as error:
            return JobSourceFetchResult(source, error=_failure_reason(error))
        return JobSourceFetchResult(source, jobs=jobs)

    async def fetch_all(self, sources: list[JobSource]) -> list[JobSourceFetchResult]:
        source_fetches = [self.fetch_source(source) for source in sources]
        return await asyncio.gather(*source_fetches)
