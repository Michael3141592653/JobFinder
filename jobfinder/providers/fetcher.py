"""Fetch jobs from many job sources in parallel, without one failure stopping the rest."""

import asyncio
from concurrent.futures import Executor

import httpx
from pydantic import ValidationError

from jobfinder.providers import PROVIDERS
from jobfinder.providers.http_client import HttpClient
from jobfinder.schema import JobSource, JobSourceFetchResult


def _failure_reason(error: Exception) -> str:
    """The error's first line, or its type when the message is empty (e.g. ReadTimeout)."""
    lines = str(error).splitlines()
    return lines[0] if lines else type(error).__name__


class JobFetcher:
    """Fetches jobs from every provider through one shared HttpClient, and parses them in
    parse_executor (a process pool in the app, a thread pool in tests)."""

    def __init__(self, http: HttpClient, parse_executor: Executor) -> None:
        self._providers = {
            name: provider(http, parse_executor) for name, provider in PROVIDERS.items()
        }

    async def fetch_source(self, source: JobSource) -> JobSourceFetchResult:
        try:
            jobs = await self._providers[source.provider].fetch(source.slug)
        except (httpx.HTTPError, ValidationError) as error:
            return JobSourceFetchResult(source, error=_failure_reason(error))
        return JobSourceFetchResult(source, jobs=jobs)

    async def fetch_all(self, sources: list[JobSource]) -> list[JobSourceFetchResult]:
        # TaskGroup, not gather: if one fetch fails unexpectedly, the others are cancelled
        # instead of running on with nobody waiting for them.
        async with asyncio.TaskGroup() as task_group:
            fetch_tasks = [task_group.create_task(self.fetch_source(source)) for source in sources]
        return [fetch_task.result() for fetch_task in fetch_tasks]
