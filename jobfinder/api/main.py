"""Every router of the API in one, behind the service token."""

from fastapi import APIRouter, Security

from jobfinder.api.dependencies.auth import require_service_token
from jobfinder.api.routers import jobs

api_router = APIRouter(dependencies=[Security(require_service_token)])  # /docs stays open
api_router.include_router(jobs.router)
