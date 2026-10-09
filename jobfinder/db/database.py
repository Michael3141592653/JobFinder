"""The database the app talks to: create one per app and open a short session per unit of work.
Async (psycopg's AsyncConnection), so waiting on Postgres never blocks the API's event loop."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import psycopg

from jobfinder.db.queries import load_query
from jobfinder.db.session import DatabaseSession

CHECK_TIMEOUT_SECONDS = 10  # without it, an unreachable server can hang for minutes on Windows
_TRY_LOCK_REFRESHES = load_query("try_lock_refreshes")


class RefreshAlreadyRunningError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("another refresh is running: try again when it is done")


class Database:
    """Where database sessions come from. Long-lived: one per app, reused for every session."""

    def __init__(self, url: str) -> None:
        self._url = url

    async def check(self) -> None:
        """Fail now if the database can't be reached, e.g. at startup."""
        connection = await psycopg.AsyncConnection.connect(
            self._url, connect_timeout=CHECK_TIMEOUT_SECONDS
        )
        await connection.close()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[DatabaseSession]:
        """A fresh connection and transaction, closed afterwards. Save with session.commit()."""
        # ponytail: one connection per session; take it from a psycopg_pool.AsyncConnectionPool
        # opened once here when requests come often (search, phase 2).
        async with (
            await psycopg.AsyncConnection.connect(self._url) as connection,
            DatabaseSession(connection) as session,
        ):
            yield session

    @asynccontextmanager
    async def refresh_session(self) -> AsyncGenerator[DatabaseSession]:
        """A session that only one refresh holds at a time, across processes and machines. Hold it
        from before the fetch until after the commit, so an older fetch can never be stored over
        a newer one. Fails right away if another refresh holds it: that one is already fetching.
        """
        # The lock and the writes share one connection: if it drops, Postgres releases the lock,
        # and the same dead connection can no longer write, so a run that lost the lock never
        # commits. The lock is taken in autocommit, so no transaction is open during the fetch.
        async with await psycopg.AsyncConnection.connect(self._url, autocommit=True) as connection:
            lock_cursor = await connection.execute(_TRY_LOCK_REFRESHES)
            [lock_taken] = await lock_cursor.fetchone()
            if not lock_taken:
                raise RefreshAlreadyRunningError
            await connection.set_autocommit(False)  # from here, the work is one transaction
            async with DatabaseSession(connection) as session:
                yield session
