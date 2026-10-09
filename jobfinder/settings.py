"""The app's settings, from the environment. `just` loads .env (see .env.example)."""

import os


def _required_setting(name: str) -> str:
    setting = os.environ.get(name)
    if not setting:
        raise RuntimeError(f"{name} is not set: copy .env.example to .env")
    return setting


def database_url() -> str:
    return _required_setting("DATABASE_URL")


def service_token() -> str:
    """The token machine callers (e.g. the scheduler) send as "Authorization: Bearer <token>"."""
    return _required_setting("SERVICE_TOKEN")
