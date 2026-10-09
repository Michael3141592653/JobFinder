import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import Executor
from typing import ClassVar

from jobfinder.providers.http_client import HttpClient
from jobfinder.schema import Job


class Provider(ABC):
    """A service we read jobs from (Greenhouse, Lever, ...).

    Knows where to find a company's jobs and how to read them.

    Subclasses set `name` and implement `jobs_url` and `parse`; `fetch` is shared.
    """

    name: ClassVar[str]  # used in sources.toml

    def __init__(self, http_client: HttpClient, parse_executor: Executor) -> None:
        self._http_client = http_client
        self._parse_executor = parse_executor

    @abstractmethod
    def jobs_url(self, slug: str) -> str:
        """The API URL listing every open job of this company."""

    @classmethod
    @abstractmethod
    def parse(cls, response_body: bytes | str, slug: str) -> list[Job]:
        """Validate the response body and map each raw job to a Job."""

    async def fetch(self, slug: str) -> list[Job]:
        response_body = await self._http_client.get(self.jobs_url(slug))
        # Off the event loop: parsing a big company is pure-Python CPU work (~0.6 s for 9 MB).
        # The app passes a process pool: a thread would still hold the GIL and slow the loop;
        # tests pass a thread pool, which is faster to start.
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._parse_executor, self.parse, response_body, slug)
