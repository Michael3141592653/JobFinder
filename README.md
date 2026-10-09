# JobFinder

Personal job finder: pull jobs from the companies you follow, rank them, send a daily digest.

## Setup

Requires [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just) and Docker.

```sh
just setup       # create .venv, install deps
just db-up       # start Postgres (docker compose), with a separate test database
just db-migrate  # create or update the tables (alembic upgrade head)
just run-api     # serve the API on http://localhost:8000 (docs at /docs)
just test        # store tests are skipped when Postgres is not running
just lint        # ruff check + format check, mypy, sqlfluff for the .sql queries
just fmt
```

To fetch every job source and store the jobs, with the API running:

```sh
curl -X POST -H "Authorization: Bearer $SERVICE_TOKEN" http://localhost:8000/jobs/refresh
```

The app reads `DATABASE_URL` and `SERVICE_TOKEN` (tests: `TEST_DATABASE_URL`) from `.env` or the environment, which wins; there are no defaults, and the app won't start if one is missing.
After changing the schema, add a migration with `uv run alembic revision -m "<what changed>"`.

