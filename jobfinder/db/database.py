"""The database the app talks to: create one per app and open a short session per unit of work."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Self

import psycopg

from jobfinder.db.session import DatabaseSession
from jobfinder.db.settings import database_url

CHECK_TIMEOUT_SECONDS = 10  # without it, an unreachable server can hang for minutes on Windows


class Database:
    """Where database sessions come from. Long-lived: one per app, reused for every session."""

    def __init__(self, url: str) -> None:
        self._url = url

    @classmethod
    def from_env(cls) -> Self:
        """The database in $DATABASE_URL; fails right away if it is not set."""
        return cls(database_url())

    def check(self) -> None:
        """Fail now if the database can't be reached, e.g. before a slow fetch."""
        psycopg.connect(self._url, connect_timeout=CHECK_TIMEOUT_SECONDS).close()

    @contextmanager
    def session(self) -> Iterator[DatabaseSession]:
        """A fresh connection and transaction, closed afterwards. Save with session.commit()."""
        # ponytail: one connection per session; take it from a psycopg_pool.ConnectionPool
        # opened once here when the FastAPI app arrives (many sessions per second).
        with psycopg.connect(self._url) as connection, DatabaseSession(connection) as session:
            yield session
