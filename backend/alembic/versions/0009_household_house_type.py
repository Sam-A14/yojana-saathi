"""household house_type

Adds one household fact: what kind of house the family lives in (no_house, kutcha or pucca).
Nullable on purpose: an unanswered question must stay different from any answer, because the rules
engine turns a missing fact into "unknown", never into "not eligible". Existing households stay NULL
(unknown). No CHECK constraint, like `education` and `current_study_level`: the API refuses other
words, and a new kind should not need a migration.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-28 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("households", sa.Column("house_type", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("households", "house_type")
