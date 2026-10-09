import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg

from jobfinder.config import SourcesConfig
from jobfinder.db.settings import database_url
from jobfinder.db.store import JobStore
from jobfinder.fetcher import JobFetcher
from jobfinder.http_client import HttpClient
from jobfinder.providers import PROVIDERS
from jobfinder.schema import Job, JobSource, JobSourceFetchResult

# ponytail: fixed retention; make it a setting if someone needs closed jobs for longer.
KEEP_CLOSED_JOBS = timedelta(days=30)


def _print_jobs(jobs: list[Job]) -> None:
    for job in jobs:
        print(f"{job.title} | {'; '.join(job.locations)} | {job.url}")
    print(f"{len(jobs)} jobs")


def _failure_line(result: JobSourceFetchResult) -> str:
    return f"{result.source}: FAILED: {result.error}"


def _status_line(result: JobSourceFetchResult, new_job_count: int) -> str:
    if result.error:
        return _failure_line(result)
    return f"{result.source}: {len(result.jobs)} jobs ({new_job_count} new)"


def _print_summary(results: list[JobSourceFetchResult], new_job_counts: list[int]) -> None:
    for result, new_job_count in zip(results, new_job_counts, strict=True):
        print(_status_line(result, new_job_count))
    job_count = sum(len(result.jobs) for result in results)
    print(f"{job_count} jobs total ({sum(new_job_counts)} new)")


async def _fetch_all_jobs(sources: list[JobSource]) -> list[JobSourceFetchResult]:
    async with HttpClient() as http:
        return await JobFetcher(http).fetch_all(sources)


def _store_results(store: JobStore, results: list[JobSourceFetchResult]) -> list[int]:
    """Save every result and return each source's count of new jobs."""
    seen_at = datetime.now(UTC)
    new_job_counts = [store.save(result, seen_at) for result in results]
    store.delete_closed_jobs(closed_before=seen_at - KEEP_CLOSED_JOBS)
    return new_job_counts


def _cmd_run(args: argparse.Namespace) -> None:
    config = SourcesConfig.from_toml(args.sources_file)
    # Connect before fetching: a missing .env or a stopped Postgres fails before the slow part.
    with psycopg.connect(database_url()) as connection:
        results = asyncio.run(_fetch_all_jobs(config.sources()))
        new_job_counts = _store_results(JobStore(connection), results)
    _print_summary(results, new_job_counts)


def _cmd_fetch(args: argparse.Namespace) -> None:
    [result] = asyncio.run(_fetch_all_jobs([JobSource(args.provider, args.slug)]))
    if result.error:
        print(_failure_line(result))
    else:
        _print_jobs(result.jobs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobfinder")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="fetch and store the jobs of every source in the file")
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
