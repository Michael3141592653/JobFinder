"""Load the SQL queries (one .sql file each in db/queries, kept out of the Python code) and run
the ones that return a single value."""

from importlib.resources import files
from typing import Any

import psycopg

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
