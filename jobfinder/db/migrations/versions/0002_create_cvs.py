"""create cvs

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-12 10:00:00.000000
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # parsed_cv is what the LLM read, then what the user corrected: markdown can be parsed again.
    op.execute("""
        CREATE TABLE cvs (
            id          bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            file_name   text        NOT NULL,
            file_bytes  bytea       NOT NULL,
            markdown    text        NOT NULL,
            parsed_cv   jsonb       NOT NULL,
            uploaded_at timestamptz NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE cvs")
