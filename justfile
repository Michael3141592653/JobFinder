set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]
set dotenv-load

default:
    @just --list

# install deps into .venv
setup:
    uv sync

# start Postgres and wait until it accepts connections
db-up:
    docker compose up -d --wait

db-migrate:
    uv run alembic upgrade head

run *args:
    uv run python -m jobfinder run {{args}}

test *args:
    uv run pytest {{args}}

lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run sqlfluff lint jobfinder/db/queries

fmt:
    uv run ruff check --fix .
    uv run ruff format .
    uv run sqlfluff fix jobfinder/db/queries
