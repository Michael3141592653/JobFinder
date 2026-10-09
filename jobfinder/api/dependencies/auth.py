"""Who may call the API: every request must send the service token as a Bearer token."""

import secrets
from typing import Annotated

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr

_BEARER_SCHEME = HTTPBearer()


async def require_service_token(
    request: Request,
    authorization: Annotated[HTTPAuthorizationCredentials, Security(_BEARER_SCHEME)],
) -> None:
    """Rejects the request unless it sends "Authorization: Bearer <the app's token>"; a missing
    header is a 401 too."""
    app_service_token: SecretStr = request.app.state.service_token
    # compare_digest takes as long for a wrong token as for a right one: no timing hints
    if not secrets.compare_digest(
        authorization.credentials.encode(), app_service_token.get_secret_value().encode()
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "invalid service token",
            headers={"WWW-Authenticate": "Bearer"},  # tells the client which scheme to use
        )
