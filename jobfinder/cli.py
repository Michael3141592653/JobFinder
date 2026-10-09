import argparse
import asyncio
from pathlib import Path

from jobfinder.config import SourcesConfig
from jobfinder.fetcher import FetchResult, JobFetcher
from jobfinder.http_client import HttpClient
from jobfinder.providers import PROVIDERS
from jobfinder.schema import Job, JobSource


def _print_jobs(jobs: list[Job]) -> None:
    for job in jobs:
        print(f"{job.title} | {'; '.join(job.locations)} | {job.url}")
    print(f"{len(jobs)} jobs")


def _status_line(result: FetchResult) -> str:
    status = f"FAILED: {result.error}" if result.error else f"{len(result.jobs)} jobs"
    return f"{result.source}: {status}"


def _print_summary(results: list[FetchResult]) -> None:
    for result in results:
        print(_status_line(result))
    print(f"{sum(len(result.jobs) for result in results)} jobs total")


async def _fetch_all_jobs(sources: list[JobSource]) -> list[FetchResult]:
    async with HttpClient() as http:
        return await JobFetcher(http).fetch_all(sources)


def _cmd_run(args: argparse.Namespace) -> None:
    config = SourcesConfig.from_toml(args.sources_file)
    results = asyncio.run(_fetch_all_jobs(config.sources()))
    _print_summary(results)


def _cmd_fetch(args: argparse.Namespace) -> None:
    [result] = asyncio.run(_fetch_all_jobs([JobSource(args.provider, args.slug)]))
    if result.error:
        print(_status_line(result))
    else:
        _print_jobs(result.jobs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobfinder")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="fetch the jobs of every source in the sources file")
    run.add_argument("--sources-file", type=Path, default=Path("sources.toml"))
    run.set_defaults(handler=_cmd_run)

    fetch = commands.add_parser("fetch", help="fetch one company's jobs and print them")
    fetch.add_argument("provider", choices=PROVIDERS)
    fetch.add_argument("slug", help="company slug, e.g. datadog or spotify")
    fetch.set_defaults(handler=_cmd_fetch)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    args.handler(args)
