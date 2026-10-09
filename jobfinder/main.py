"""The app: builds the services once, then serves the API. Run with `just run-api`; the docs
are at /docs."""

import logging
from collections.abc import AsyncGenerator, Callable
from concurrent.futures import Executor, ProcessPoolExecutor
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pydantic import SecretStr

from jobfinder.api.exceptions import add_exception_handlers
from jobfinder.api.main import api_router
from jobfinder.db.database import Database
from jobfinder.providers.fetcher import JobFetcher
from jobfinder.providers.http_client import HttpClient
from jobfinder.services.refresher import JobRefresher
from jobfinder.settings import Settings
from jobfinder.sources import SOURCES_FILE

# Processes that parse the job boards' responses. Each one starts on the first refresh after
# startup (about 2 s each on Windows), then stays for the next ones.
PARSE_PROCESSES = 4


def _lifespan(
    database: Database, http_client: HttpClient, parse_executor: Executor
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """At startup, fail if Postgres can't be reached; at shutdown, close the HTTP connections
    and stop the parse processes."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        await database.check()
        async with http_client:
            with parse_executor:
                yield

    return lifespan


def create_app(
    database: Database,
    http_client: HttpClient,
    sources_file: Path,
    service_token: SecretStr,
    parse_executor: Executor,
) -> FastAPI:
    """The app with its dependencies passed in, so tests can pass a fake provider server and
    parse in threads. app.state holds only what the endpoints read."""
    app = FastAPI(title="JobFinder", lifespan=_lifespan(database, http_client, parse_executor))
    app.state.job_refresher = JobRefresher(JobFetcher(http_client, parse_executor), database)
    app.state.sources_file = sources_file
    app.state.service_token = service_token
    app.include_router(api_router)
    add_exception_handlers(app)
    return app


def app_from_env() -> FastAPI:
    """The real app, for uvicorn's --factory: fails at startup if a setting is missing."""
    # uvicorn configures only its own loggers: without this, the app's INFO lines are dropped.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
    settings = Settings()
    return create_app(
        Database(settings.database_url),
        HttpClient(),
        SOURCES_FILE,
        settings.service_token,
        ProcessPoolExecutor(max_workers=PARSE_PROCESSES),
    )
