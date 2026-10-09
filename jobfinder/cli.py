import argparse
import asyncio
from pathlib import Path

from jobfinder.config import BoardsConfig
from jobfinder.http_client import HttpClient
from jobfinder.ingest import BoardResult, Ingestor
from jobfinder.schema import Board, Job
from jobfinder.sources import SOURCES


def _print_jobs(jobs: list[Job]) -> None:
    for job in jobs:
        print(f"{job.title} | {'; '.join(job.locations)} | {job.url}")
    print(f"{len(jobs)} jobs")


def _print_summary(results: list[BoardResult]) -> None:
    for result in results:
        status = f"FAILED: {result.error}" if result.error else f"{len(result.jobs)} jobs"
        print(f"{result.board}: {status}")
    print(f"{sum(len(result.jobs) for result in results)} jobs total")


async def _download_board(board: Board) -> BoardResult:
    async with HttpClient() as http:
        return await Ingestor(http).fetch_board(board)


async def _download_all(boards: list[Board]) -> list[BoardResult]:
    async with HttpClient() as http:
        return await Ingestor(http).fetch_all(boards)


def _cmd_run(args: argparse.Namespace) -> None:
    config = BoardsConfig.from_toml(args.boards_file)
    results = asyncio.run(_download_all(config.boards()))
    _print_summary(results)


def _cmd_fetch(args: argparse.Namespace) -> None:
    result = asyncio.run(_download_board(Board(args.source, args.slug)))
    if result.error:
        print(f"{result.board}: FAILED: {result.error}")
    else:
        _print_jobs(result.jobs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobfinder")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="fetch every board in the boards file")
    run.add_argument("--boards-file", type=Path, default=Path("boards.toml"))
    run.set_defaults(handler=_cmd_run)

    fetch = commands.add_parser("fetch", help="fetch one board and print its jobs")
    fetch.add_argument("source", choices=SOURCES)
    fetch.add_argument("slug", help="company board slug, e.g. datadog or spotify")
    fetch.set_defaults(handler=_cmd_fetch)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    args.handler(args)
