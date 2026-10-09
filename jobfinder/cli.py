import argparse
import asyncio
from pathlib import Path

from jobfinder.config import SourcesConfig
from jobfinder.db.database import Database, UpdateAlreadyRunningError
from jobfinder.fetcher import JobFetcher
from jobfinder.http_client import HttpClient
from jobfinder.providers import PROVIDERS
from jobfinder.schema import Job, JobSource, JobSourceFetchResult
from jobfinder.updater import JobUpdater, SourceUpdate


def _print_jobs(jobs: list[Job]) -> None:
    for job in jobs:
        print(f"{job.title} | {'; '.join(job.locations)} | {job.url}")
    print(f"{len(jobs)} jobs")


def _failure_line(result: JobSourceFetchResult) -> str:
    return f"{result.source}: FAILED: {result.error}"


def _status_line(update: SourceUpdate) -> str:
    if update.result.error:
        return _failure_line(update.result)
    return f"{update.result.source}: {len(update.result.jobs)} jobs ({update.new_job_count} new)"


def _print_summary(updates: list[SourceUpdate]) -> None:
    for update in updates:
        print(_status_line(update))
    job_count = sum(len(update.result.jobs) for update in updates)
    new_job_count = sum(update.new_job_count for update in updates)
    print(f"{job_count} jobs total ({new_job_count} new)")


async def _fetch_source(source: JobSource) -> JobSourceFetchResult:
    async with HttpClient() as http:
        return await JobFetcher(http).fetch_source(source)


async def _update_jobs(sources: list[JobSource]) -> list[SourceUpdate]:
    database = Database.from_env()
    database.check()  # fail before the slow fetch if DATABASE_URL is missing or Postgres is down
    async with HttpClient() as http:
        return await JobUpdater(JobFetcher(http), database).update(sources)


def _cmd_run(args: argparse.Namespace) -> None:
    config = SourcesConfig.from_toml(args.sources_file)
    try:
        updates = asyncio.run(_update_jobs(config.sources()))
    except UpdateAlreadyRunningError as error:
        raise SystemExit(f"jobfinder: {error}") from None
    _print_summary(updates)


def _cmd_fetch(args: argparse.Namespace) -> None:
    result = asyncio.run(_fetch_source(JobSource(args.provider, args.slug)))
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
