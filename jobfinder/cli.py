import argparse
import asyncio

import httpx

from jobfinder.schema import Job
from jobfinder.sources import greenhouse


def _print_jobs(jobs: list[Job]) -> None:
    for job in jobs:
        print(f"{job.title} | {job.location} | {job.url}")
    print(f"{len(jobs)} jobs")


async def _download_board(board: str) -> list[Job]:
    async with httpx.AsyncClient(timeout=30) as client:
        return await greenhouse.fetch(client, board)


def _cmd_run(_args: argparse.Namespace) -> None:
    print("jobfinder: nothing to run yet")


def _cmd_fetch(args: argparse.Namespace) -> None:
    jobs = asyncio.run(_download_board(args.board))
    _print_jobs(jobs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobfinder")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("run").set_defaults(handler=_cmd_run)

    fetch = commands.add_parser("fetch", help="fetch one board and print its jobs")
    fetch.add_argument("source", choices=["greenhouse"])
    fetch.add_argument("board", help="board slug, e.g. datadog")
    fetch.set_defaults(handler=_cmd_fetch)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    args.handler(args)
