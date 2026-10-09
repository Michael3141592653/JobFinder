"""The app: builds the services once, then serves the API. Run with `just run-api`; the docs
are at /docs."""

from collections.abc import AsyncGenerator
from concurrent.futures import Executor, ProcessPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pydantic import SecretStr

from jobfinder.api.exceptions import add_exception_handlers
from jobfinder.api.main import api_router
from jobfinder.config import SOURCES_FILE
from jobfinder.db.database import Database
from jobfinder.providers.fetcher import JobFetcher
from jobfinder.providers.http_client import HttpClient
from jobfinder.services.refresher import JobRefresher
from jobfinder.settings import Settings

# Processes that parse the job boards' responses. Each one starts on the first refresh after
# startup (about 2 s each on Windows), then stays for the next ones.
PARSE_PROCESSES = 4


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """At startup, fail if Postgres can't be reached; at shutdown, close the HTTP connections
    and stop the parse processes."""
    await app.state.database.check()
    async with app.state.http_client:
        yield
    if app.state.parse_executor:
        app.state.parse_executor.shutdown(cancel_futures=True)


def create_app(
    database: Database,
    http_client: HttpClient,
    sources_file: Path,
    service_token: SecretStr,
    parse_executor: Executor | None = None,
) -> FastAPI:
    """The app with its dependencies passed in, so tests can pass a fake provider server.
    parse_executor None parses in threads: fine for tests, but it slows the event loop."""
    app = FastAPI(title="JobFinder", lifespan=_lifespan)
    app.state.database = database
    app.state.http_client = http_client
    app.state.parse_executor = parse_executor
    app.state.job_refresher = JobRefresher(JobFetcher(http_client, parse_executor), database)
    app.state.sources_file = sources_file
    app.state.service_token = service_token
    app.include_router(api_router)
    add_exception_handlers(app)
    return app


def app_from_env() -> FastAPI:
    """The real app, for uvicorn's --factory: fails at startup if a setting is missing."""
    settings = Settings()
    return create_app(
        Database(settings.database_url),
        HttpClient(),
        SOURCES_FILE,
        settings.service_token,
        ProcessPoolExecutor(max_workers=PARSE_PROCESSES),
    )
