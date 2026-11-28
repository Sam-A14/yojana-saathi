"""member current_study_level

Adds one member fact: what the person is studying now (class_1_8, class_9_10, class_11_12,
undergraduate, postgraduate, other). Nullable on purpose: an unanswered question must stay
different from any answer, because the rules engine turns a missing fact into "unknown", never into
"not eligible". Existing members stay NULL (unknown). No CHECK constraint, like `education`: the API
refuses other words, and a new level should not need a migration.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-28 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("members", sa.Column("current_study_level", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("members", "current_study_level")
