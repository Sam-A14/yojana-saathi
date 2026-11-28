"""alerts: read_at and dedupe_key

The alerts table existed since the first migration but nothing used it. In-app alerts need two
things: "has the family seen this?" (read_at, NULL = unread) and "was this alert already made?"
(dedupe_key, so the daily job can run twice, or every day, and never repeat itself). Both are
nullable, so existing rows stay valid. The unique index is on (user_id, dedupe_key); Postgres treats
NULLs as different, so alerts without a key are never blocked.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-28 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column("dedupe_key", sa.String(), nullable=True))
    op.create_index(
        "uq_alerts_user_id_dedupe_key", "alerts", ["user_id", "dedupe_key"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_alerts_user_id_dedupe_key", table_name="alerts")
    op.drop_column("alerts", "dedupe_key")
    op.drop_column("alerts", "read_at")
