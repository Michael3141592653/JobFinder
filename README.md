# JobFinder

Personal job finder: pull jobs from the companies you follow, rank them, send a daily digest.

## Setup

Requires [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just) and Docker.

```sh
just setup       # create .venv, install deps
just db-up       # start Postgres (docker compose), with a separate test database
just db-migrate  # create or update the tables (alembic upgrade head)
just run         # fetch every job source and store the jobs
just test        # store tests are skipped when Postgres is not running
just lint        # ruff check + format check, sqlfluff for the .sql queries
just fmt
```

The app reads `DATABASE_URL` (tests: `TEST_DATABASE_URL`) from the environment; there are no defaults.
Run commands through `just` so `.env` is loaded, or set the variables yourself.
After changing the schema, add a migration with `uv run alembic revision -m "<what changed>"`.

