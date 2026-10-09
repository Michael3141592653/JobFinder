"""Every router of the API in one, behind the service token."""

from fastapi import APIRouter, Security, status

from jobfinder.api.dependencies.auth import require_service_token
from jobfinder.api.routers import jobs
from jobfinder.api.schemas.errors import ErrorResponse

api_router = APIRouter(
    dependencies=[Security(require_service_token)],  # every endpoint; /docs stays open
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing or invalid service token",
        }
    },
)
api_router.include_router(jobs.router)
