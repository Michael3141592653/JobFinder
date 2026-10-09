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
