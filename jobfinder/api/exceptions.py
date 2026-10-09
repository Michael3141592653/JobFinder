"""How the services' errors become HTTP responses."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from jobfinder.db.database import RefreshAlreadyRunningError


async def _handle_refresh_already_running(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=status.HTTP_409_CONFLICT)


def add_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RefreshAlreadyRunningError, _handle_refresh_already_running)
