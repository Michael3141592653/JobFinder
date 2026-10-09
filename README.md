# JobFinder

Personal job finder: pull jobs from the companies you follow, rank them, send a daily digest.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just).

```sh
just setup   # create .venv, install deps
just run     # python -m jobfinder run
just test
just lint    # ruff check + format check
just fmt
```

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
