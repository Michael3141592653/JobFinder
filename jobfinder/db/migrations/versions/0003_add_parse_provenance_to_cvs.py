"""add parse provenance to cvs

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13 10:00:00.000000
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # What read parsed_cv: after a prompt or model change, they tell which CVs to parse again;
    # corrected_at, which not to, as that would undo the user's corrections (null: never corrected).
    # NOT NULL with no default: no CV was stored before this migration.
    op.execute("""
        ALTER TABLE cvs
            ADD COLUMN prompt_version integer     NOT NULL,
            ADD COLUMN llm_model      text        NOT NULL,
            ADD COLUMN corrected_at   timestamptz
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE cvs
            DROP COLUMN prompt_version,
            DROP COLUMN llm_model,
            DROP COLUMN corrected_at
    """)
