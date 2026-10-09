"""Where the database is, from the environment. `just` loads .env (see .env.example)."""

import os


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set: copy .env.example to .env")
    return url
