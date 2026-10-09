"""create companies and jobs

Revision ID: 0001
Revises:
Create Date: 2026-10-09 12:45:54.368750
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE companies (
            id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            provider        text        NOT NULL,
            slug            text        NOT NULL,
            name            text        NOT NULL,
            last_fetched_at timestamptz NOT NULL,
            last_error      text,
            UNIQUE (provider, slug)
        )
    """)
    op.execute("""
        CREATE TABLE jobs (
            id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            company_id      bigint      NOT NULL REFERENCES companies ON DELETE CASCADE,
            provider_job_id text        NOT NULL,
            title           text        NOT NULL,
            locations       text[]      NOT NULL,
            url             text        NOT NULL,
            description     text        NOT NULL,
            posted_at       timestamptz NOT NULL,
            updated_at      timestamptz,
            first_seen      timestamptz NOT NULL,
            last_seen       timestamptz NOT NULL,
            closed_at       timestamptz,
            UNIQUE (company_id, provider_job_id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE jobs")
    op.execute("DROP TABLE companies")
