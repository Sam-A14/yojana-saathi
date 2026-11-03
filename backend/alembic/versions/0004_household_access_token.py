"""household access token

Households can exist before login: they are opened with a secret token whose hash is stored here.
user_id becomes nullable (login fills it in later). A CHECK stops a household having neither.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("households", sa.Column("access_token_hash", sa.String(), nullable=True))
    op.create_unique_constraint(
        op.f("uq_households_access_token_hash"), "households", ["access_token_hash"]
    )
    op.alter_column("households", "user_id", existing_type=sa.Uuid(), nullable=True)
    op.create_check_constraint(
        op.f("ck_households_has_owner"),
        "households",
        "user_id IS NOT NULL OR access_token_hash IS NOT NULL",
    )


def downgrade() -> None:
    # Households that only have a token cannot exist under the old schema, so they are removed.
    # Their members, documents and results go with them (ON DELETE CASCADE).
    op.drop_constraint(op.f("ck_households_has_owner"), "households", type_="check")
    op.execute("DELETE FROM households WHERE user_id IS NULL")
    op.alter_column("households", "user_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint(op.f("uq_households_access_token_hash"), "households", type_="unique")
    op.drop_column("households", "access_token_hash")
