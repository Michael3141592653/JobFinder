import argparse
import asyncio
from pathlib import Path

from jobfinder import http, ingest
from jobfinder.ingest import BoardResult, Boards
from jobfinder.schema import Job
from jobfinder.sources import FETCHERS


def _print_jobs(jobs: list[Job]) -> None:
    for job in jobs:
        print(f"{job.title} | {'; '.join(job.locations)} | {job.url}")
    print(f"{len(jobs)} jobs")


def _print_summary(results: list[BoardResult]) -> None:
    for result in results:
        status = f"FAILED: {result.error}" if result.error else f"{len(result.jobs)} jobs"
        print(f"{result.source}/{result.board}: {status}")
    print(f"{sum(len(result.jobs) for result in results)} jobs total")


async def _download_board(source: str, board: str) -> list[Job]:
    async with http.new_client() as client:
        return await FETCHERS[source](client, board)


async def _download_all(boards: Boards) -> list[BoardResult]:
    async with http.new_client() as client:
        return await ingest.fetch_all(client, boards)


def _cmd_run(args: argparse.Namespace) -> None:
    boards = ingest.load_boards(args.boards)
    results = asyncio.run(_download_all(boards))
    _print_summary(results)


def _cmd_fetch(args: argparse.Namespace) -> None:
    jobs = asyncio.run(_download_board(args.source, args.board))
    _print_jobs(jobs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobfinder")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="fetch every board in the boards file")
    run.add_argument("--boards", type=Path, default=Path("boards.toml"))
    run.set_defaults(handler=_cmd_run)

    fetch = commands.add_parser("fetch", help="fetch one board and print its jobs")
    fetch.add_argument("source", choices=FETCHERS)
    fetch.add_argument("board", help="board slug, e.g. datadog or spotify")
    fetch.set_defaults(handler=_cmd_fetch)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    args.handler(args)
