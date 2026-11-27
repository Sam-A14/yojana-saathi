"""household is_bpl

Adds one household fact: is the family on the Below Poverty Line list. Nullable on purpose: an
unanswered question must stay different from "no", because the rules engine turns a missing fact
into "unknown", never into "not eligible". Existing households stay NULL (unknown).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-27 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("households", sa.Column("is_bpl", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("households", "is_bpl")
