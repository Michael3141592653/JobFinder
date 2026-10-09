"""Fetch boards in parallel, without one failure stopping the rest."""

import asyncio
from dataclasses import dataclass, field

import httpx
from pydantic import ValidationError

from jobfinder.http_client import HttpClient
from jobfinder.schema import Board, Job
from jobfinder.sources import SOURCES


@dataclass
class BoardResult:
    board: Board
    jobs: list[Job] = field(default_factory=list)
    error: str | None = None


class Ingestor:
    """Fetches boards from every source through one shared HttpClient."""

    def __init__(self, http: HttpClient) -> None:
        self._sources = {name: source_class(http) for name, source_class in SOURCES.items()}

    async def fetch_board(self, board: Board) -> BoardResult:
        try:
            jobs = await self._sources[board.source].fetch(board.slug)
        except (httpx.HTTPError, ValidationError) as error:
            return BoardResult(board, error=str(error).splitlines()[0])
        return BoardResult(board, jobs=jobs)

    async def fetch_all(self, boards: list[Board]) -> list[BoardResult]:
        board_fetches = [self.fetch_board(board) for board in boards]
        return await asyncio.gather(*board_fetches)
