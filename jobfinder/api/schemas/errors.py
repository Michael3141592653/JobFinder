"""The body of every error response, as FastAPI sends it: {"detail": "..."}."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str  # why the request failed, e.g. "another refresh is running: try again ..."
