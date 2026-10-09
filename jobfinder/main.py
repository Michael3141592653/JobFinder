"""The app: builds the services once, then serves the API. Run with `just run-api`; the docs
are at /docs."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pydantic import SecretStr

from jobfinder.api.exceptions import add_exception_handlers
from jobfinder.api.main import api_router
from jobfinder.config import SOURCES_FILE
from jobfinder.db.database import Database
from jobfinder.fetcher import JobFetcher
from jobfinder.http_client import HttpClient
from jobfinder.services.refresher import JobRefresher
from jobfinder.settings import Settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """At startup, fail if Postgres can't be reached; at shutdown, close the HTTP connections."""
    await app.state.database.check()
    async with app.state.http_client:
        yield


def create_app(
    database: Database, http_client: HttpClient, sources_file: Path, service_token: SecretStr
) -> FastAPI:
    """The app with its dependencies passed in, so tests can pass a fake provider server."""
    app = FastAPI(title="JobFinder", lifespan=_lifespan)
    app.state.database = database
    app.state.http_client = http_client
    app.state.job_refresher = JobRefresher(JobFetcher(http_client), database)
    app.state.sources_file = sources_file
    app.state.service_token = service_token
    app.include_router(api_router)
    add_exception_handlers(app)
    return app


def app_from_env() -> FastAPI:
    """The real app, for uvicorn's --factory: fails at startup if a setting is missing."""
    settings = Settings()
    return create_app(
        Database(settings.database_url), HttpClient(), SOURCES_FILE, settings.service_token
    )
