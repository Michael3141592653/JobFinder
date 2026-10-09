"""Jobs: refresh them from the providers (search comes next)."""

from fastapi import APIRouter

from jobfinder.api.dependencies.jobs import JobRefresherDep, SourcesDep
from jobfinder.api.schemas.jobs import RefreshReport

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/refresh")
async def refresh_jobs(job_refresher: JobRefresherDep, sources: SourcesDep) -> RefreshReport:
    """Fetch every job source in the sources file and store the jobs. Answers when done, with
    409 Conflict if another refresh is running."""
    # ponytail: the database calls inside are sync, so they block the event loop while storing;
    # move to psycopg's AsyncConnection with the connection pool.
    source_refreshes = await job_refresher.refresh(sources)
    return RefreshReport.from_source_refreshes(source_refreshes)
