"""Fetch every configured board in parallel, without one failure stopping the rest."""

import asyncio
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from pydantic import TypeAdapter, ValidationError

from jobfinder.schema import Job
from jobfinder.sources import FETCHERS

Boards = dict[str, list[str]]  # source name -> board slugs


@dataclass
class BoardResult:
    source: str
    board: str
    jobs: list[Job] = field(default_factory=list)
    error: str | None = None


def _check_sources_exist(boards: Boards) -> None:
    unknown = boards.keys() - FETCHERS.keys()
    if unknown:
        raise ValueError(f"unknown sources {sorted(unknown)}, expected some of {sorted(FETCHERS)}")


def load_boards(path: Path) -> Boards:
    with path.open("rb") as file:
        boards = TypeAdapter(Boards).validate_python(tomllib.load(file))
    _check_sources_exist(boards)
    return boards


async def _fetch_board(client: httpx.AsyncClient, source: str, board: str) -> BoardResult:
    try:
        jobs = await FETCHERS[source](client, board)
    except (httpx.HTTPError, ValidationError) as error:
        return BoardResult(source, board, error=str(error).splitlines()[0])
    return BoardResult(source, board, jobs=jobs)


async def fetch_all(client: httpx.AsyncClient, boards: Boards) -> list[BoardResult]:
    board_fetches = [
        _fetch_board(client, source, board) for source, slugs in boards.items() for board in slugs
    ]
    return await asyncio.gather(*board_fetches)
