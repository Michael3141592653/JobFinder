"""A session with the database: one transaction, saved only when you call commit()."""

from types import TracebackType
from typing import Self

import psycopg

from jobfinder.db.store import JobStore


class DatabaseSession:
    """Groups database work into one transaction. Nothing is saved unless you call commit():
    leaving the `with` block without it, or because of an exception, rolls everything back."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection
        self.jobs = JobStore(connection)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.rollback()  # after commit() there is nothing left to roll back
