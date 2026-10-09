"""Fetch every configured board in parallel, without one failure stopping the rest."""

import asyncio
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from pydantic import RootModel, ValidationError, field_validator

from jobfinder.http import HttpClient
from jobfinder.schema import Board, Job
from jobfinder.sources import SOURCES


class BoardsConfig(RootModel[dict[str, list[str]]]):
    """The boards file's content: source name -> slugs, e.g. greenhouse = ["datadog"]."""

    @field_validator("root")
    @classmethod
    def _sources_must_exist(cls, slugs_by_source: dict[str, list[str]]) -> dict[str, list[str]]:
        unknown = slugs_by_source.keys() - SOURCES.keys()
        if unknown:
            raise ValueError(f"unknown sources {sorted(unknown)}, known: {sorted(SOURCES)}")
        return slugs_by_source

    @classmethod
    def from_toml(cls, boards_file: Path) -> "BoardsConfig":
        with boards_file.open("rb") as file:
            return cls.model_validate(tomllib.load(file))

    def boards(self) -> list[Board]:
        return [Board(source, slug) for source, slugs in self.root.items() for slug in slugs]


@dataclass
class BoardResult:
    board: Board
    jobs: list[Job] = field(default_factory=list)
    error: str | None = None


class Ingestor:
    """Fetches boards from every source through one shared HttpClient."""

    def __init__(self, http: HttpClient) -> None:
        self._sources = {name: source_class(http) for name, source_class in SOURCES.items()}

    async def _fetch_board(self, board: Board) -> BoardResult:
        try:
            jobs = await self._sources[board.source].fetch(board.slug)
        except (httpx.HTTPError, ValidationError) as error:
            return BoardResult(board, error=str(error).splitlines()[0])
        return BoardResult(board, jobs=jobs)

    async def fetch_all(self, boards: list[Board]) -> list[BoardResult]:
        board_fetches = [self._fetch_board(board) for board in boards]
        return await asyncio.gather(*board_fetches)
