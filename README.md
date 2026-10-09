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

## Terms

| Term | Meaning | In code |
|---|---|---|
| provider | a service we read jobs from: an ATS (Greenhouse, Lever, ...) or a job search API (Adzuna) | `Provider` subclasses, `PROVIDERS` |
| slug | a company's id on a provider, from its careers page URL: `datadog` in `boards.greenhouse.io/datadog` | `slug: str` |
| job source | a company we follow on one provider: provider + slug, e.g. `greenhouse/datadog` | `JobSource`, `sources: list[JobSource]` |
| sources file | `sources.toml`: the job sources to fetch, as slugs per provider; `run` fetches all of them | `sources_file` (path), `SourcesConfig` (content) |
| response body | the raw body of a provider's HTTP response, before parsing | `response_body` |
| raw job | one job as a provider's API returns it, before mapping | `_GreenhouseRawJob`, `_LeverRawJob` |
| job | a raw job mapped to our common shape, the same for every provider | `Job` |
| job source fetch result | the outcome of fetching one job source: its jobs, or why it failed | `JobSourceFetchResult` |
| company | a job source as stored in the database, with its display name and last fetch error | `companies` table |
| first seen / last seen | the first and latest run that found a job; a job is new when first seen in this run | `first_seen`, `last_seen` |
| closed job | a job missing from its source's latest successful fetch; deleted after 30 days | `closed_at`, `delete_closed_jobs` |
