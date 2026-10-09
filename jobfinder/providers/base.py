from abc import ABC, abstractmethod
from typing import ClassVar

from jobfinder.http_client import HttpClient
from jobfinder.schema import Job


class Provider(ABC):
    """A service we read jobs from (Greenhouse, Lever, ...).

    Knows where to find a company's jobs and how to read them.

    Subclasses set `name` and implement `jobs_url` and `parse`; `fetch` is shared.
    """

    name: ClassVar[str]  # used in sources.toml and on the command line

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    @abstractmethod
    def jobs_url(self, slug: str) -> str:
        """The API URL listing every open job of this company."""

    @classmethod
    @abstractmethod
    def parse(cls, response_body: bytes | str, slug: str) -> list[Job]:
        """Validate the response body and map each raw job to a Job."""

    async def fetch(self, slug: str) -> list[Job]:
        response_body = await self._http.get(self.jobs_url(slug))
        return self.parse(response_body, slug)
