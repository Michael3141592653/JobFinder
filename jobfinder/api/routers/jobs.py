"""Jobs: refresh them from the providers (search comes next)."""

from fastapi import APIRouter, status

from jobfinder.api.dependencies.jobs import JobRefresherDep, SourcesDep
from jobfinder.api.schemas.errors import ErrorResponse
from jobfinder.api.schemas.jobs import RefreshReport

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "/refresh",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Another refresh is running",
        }
    },
)
async def refresh_jobs(job_refresher: JobRefresherDep, sources: SourcesDep) -> RefreshReport:
    """Fetch every job source in the sources file and store the jobs. Answers when done."""
    source_refreshes = await job_refresher.refresh(sources)
    return RefreshReport.from_source_refreshes(source_refreshes)
