# JobFinder

Personal job finder: pull postings from ATS boards, rank them, send a daily digest.

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
| source | where we read jobs from: an ATS (Greenhouse, Lever, ...) or a job search API (Adzuna) | `Source` subclasses, `SOURCES` |
| slug | a company's id in its board URL: `datadog` in `boards.greenhouse.io/datadog` | `slug: str` |
| board | one company's job listing on one source: source + slug | `Board`, `boards: list[Board]` |
| response body | the raw body of a source's HTTP response, before parsing | `response_body` |
| boards file | `boards.toml`: the companies to follow, as slugs per source; `run` fetches all of them | `boards_file` (path), `BoardsConfig` (content) |
| job | one posting, the same shape for every source | `Job` |
