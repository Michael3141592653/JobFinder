"""The database the app talks to: create one per app and open a short session per unit of work."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Self

import psycopg

from jobfinder.db.queries import load_query
from jobfinder.db.session import DatabaseSession
from jobfinder.db.settings import database_url

CHECK_TIMEOUT_SECONDS = 10  # without it, an unreachable server can hang for minutes on Windows
_TRY_LOCK_UPDATES = load_query("try_lock_updates")


class UpdateAlreadyRunningError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("another update is running: try again when it is done")


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
    def session(self) -> Generator[DatabaseSession]:
        """A fresh connection and transaction, closed afterwards. Save with session.commit()."""
        # ponytail: one connection per session; take it from a psycopg_pool.ConnectionPool
        # opened once here when the FastAPI app arrives (many sessions per second).
        with psycopg.connect(self._url) as connection, DatabaseSession(connection) as session:
            yield session

    @contextmanager
    def update_session(self) -> Generator[DatabaseSession]:
        """A session that only one update holds at a time, across processes and machines. Hold it
        from before the fetch until after the commit, so an older fetch can never be stored over
        a newer one. Fails right away if another update holds it: that one is already fetching.
        """
        # The lock and the writes share one connection: if it drops, Postgres releases the lock,
        # and the same dead connection can no longer write, so a run that lost the lock never
        # commits. The lock is taken in autocommit, so no transaction is open during the fetch.
        with psycopg.connect(self._url, autocommit=True) as connection:
            [lock_taken] = connection.execute(_TRY_LOCK_UPDATES).fetchone()
            if not lock_taken:
                raise UpdateAlreadyRunningError
            connection.autocommit = False  # from here, the session's work is one transaction
            with DatabaseSession(connection) as session:
                yield session
