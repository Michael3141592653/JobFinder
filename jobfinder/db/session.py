"""A session with the database: one transaction, saved only when you call commit()."""

from types import TracebackType
from typing import Self

import psycopg

from jobfinder.db.store import JobStore


class DatabaseSession:
    """Groups database work into one transaction. Nothing is saved unless you call commit():
    leaving the `async with` block without it, or because of an exception, rolls it all back."""

    def __init__(self, connection: psycopg.AsyncConnection) -> None:
        self._connection = connection
        self.jobs = JobStore(connection)

    async def commit(self) -> None:
        await self._connection.commit()

    async def rollback(self) -> None:
        await self._connection.rollback()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.rollback()  # after commit() there is nothing left to roll back
