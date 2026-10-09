"""The SQL queries, one per file, kept out of the Python code."""

from pathlib import Path

QUERIES = Path(__file__).parent


def load_query(name: str) -> str:
    return (QUERIES / f"{name}.sql").read_text(encoding="utf-8")
