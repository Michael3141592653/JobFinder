"""What the jobs endpoints need, injected with Depends: the refresher built at startup (in
app.state) and the sources."""

from typing import Annotated

from fastapi import Depends, Request

from jobfinder.config import SourcesConfig
from jobfinder.schema import JobSource
from jobfinder.services.refresher import JobRefresher


# async when there is no blocking work: FastAPI runs a plain `def` dependency in a thread pool.
async def _job_refresher(request: Request) -> JobRefresher:
    return request.app.state.job_refresher


def _sources(request: Request) -> list[JobSource]:
    # Plain def: reading the file blocks, so FastAPI runs it in a thread pool, off the event loop.
    # Read on every request, so edits to the sources file apply without a restart.
    return SourcesConfig.from_toml(request.app.state.sources_file).sources()


JobRefresherDep = Annotated[JobRefresher, Depends(_job_refresher)]
SourcesDep = Annotated[list[JobSource], Depends(_sources)]
