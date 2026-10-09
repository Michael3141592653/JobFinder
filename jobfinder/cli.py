import argparse
import asyncio

import httpx

from jobfinder.schema import Job
from jobfinder.sources import FETCHERS


def _print_jobs(jobs: list[Job]) -> None:
    for job in jobs:
        print(f"{job.title} | {'; '.join(job.locations)} | {job.url}")
    print(f"{len(jobs)} jobs")


async def _download_board(source: str, board: str) -> list[Job]:
    async with httpx.AsyncClient(timeout=30) as client:
        return await FETCHERS[source](client, board)


def _cmd_run(_args: argparse.Namespace) -> None:
    print("jobfinder: nothing to run yet")


def _cmd_fetch(args: argparse.Namespace) -> None:
    jobs = asyncio.run(_download_board(args.source, args.board))
    _print_jobs(jobs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobfinder")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("run").set_defaults(handler=_cmd_run)

    fetch = commands.add_parser("fetch", help="fetch one board and print its jobs")
    fetch.add_argument("source", choices=FETCHERS)
    fetch.add_argument("board", help="board slug, e.g. datadog or spotify")
    fetch.set_defaults(handler=_cmd_fetch)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    args.handler(args)
