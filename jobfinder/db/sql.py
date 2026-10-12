"""Load the SQL queries (one .sql file each in db/queries, kept out of the Python code) and run
the ones that return a single value or a row."""

from importlib.resources import files
from typing import Any

import psycopg
from psycopg.rows import class_row

QUERIES = files("jobfinder.db.queries")


def load_query(name: str) -> str:
    return (QUERIES / f"{name}.sql").read_text(encoding="utf-8")


async def fetch_value(
    connection: psycopg.AsyncConnection, query: str, params: dict[str, Any] | None = None
) -> Any:
    """The single value a query returns, e.g. an id or a count. Fails if it returns no row."""
    cursor = await connection.execute(query, params)
    row = await cursor.fetchone()
    if row is None:
        raise LookupError(f"query returned no row: {query}")
    return row[0]


async def find_row[RowType](
    connection: psycopg.AsyncConnection,
    query: str,
    params: dict[str, Any],
    row_type: type[RowType],
) -> RowType | None:
    """The query's first row as a row_type, built from its columns by name; None if no row."""
    async with connection.cursor(row_factory=class_row(row_type)) as row_cursor:
        await row_cursor.execute(query, params)
        return await row_cursor.fetchone()
