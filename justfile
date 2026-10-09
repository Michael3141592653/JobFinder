set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

# install deps into .venv
setup:
    uv sync

run *args:
    uv run python -m jobfinder run {{args}}

test *args:
    uv run pytest {{args}}

lint:
    uv run ruff check .
    uv run ruff format --check .

fmt:
    uv run ruff check --fix .
    uv run ruff format .
