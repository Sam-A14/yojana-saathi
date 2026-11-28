"""scheme_versions.not_checked_en / not_checked_hi

The conditions of a scheme that this app does not check, in plain words, shown to families on the
scheme page as "What we did not check". Two JSONB lists of strings. The English list is never NULL
(an empty list means there is nothing to say), so existing versions get []. The Hindi list is NULL
until someone writes it; the page then shows the English one.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-28 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scheme_versions",
        sa.Column(
            "not_checked_en",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "scheme_versions", sa.Column("not_checked_hi", postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("scheme_versions", "not_checked_hi")
    op.drop_column("scheme_versions", "not_checked_en")
