from abc import ABC, abstractmethod
from typing import ClassVar

from jobfinder.http_client import HttpClient
from jobfinder.schema import Job


class Source(ABC):
    """Where we read jobs from (Greenhouse, Lever, ...): where a board lives and how to read it.

    Subclasses set `name` and implement `board_url` and `parse`; `fetch` is shared.
    """

    name: ClassVar[str]  # used in boards.toml and on the command line

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    @abstractmethod
    def board_url(self, slug: str) -> str:
        """The API URL listing every open job on this board."""

    @classmethod
    @abstractmethod
    def parse(cls, response_body: bytes | str, slug: str) -> list[Job]:
        """Validate the response body and map each raw job to a Job."""

    async def fetch(self, slug: str) -> list[Job]:
        response_body = await self._http.get(self.board_url(slug))
        return self.parse(response_body, slug)
