"""review items: validation result, quotes and raw model output

The LLM pipeline saves every proposal, valid or not. These columns hold what a reviewer needs:
whether it passed the validator and why not, one source quote per rule, and the model's exact text.
is_valid defaults to false so an old row with no validation record is never mistaken for a good one
(nothing wrote review_items before this migration).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-02 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("review_items", sa.Column("scheme_slug", sa.String(), nullable=True))
    op.add_column("review_items", sa.Column("source_url", sa.String(), nullable=True))
    op.add_column(
        "review_items",
        sa.Column("is_valid", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    for name in ("validation_errors", "source_quotes"):
        op.add_column(
            "review_items",
            sa.Column(
                name, postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
            ),
        )
    op.add_column("review_items", sa.Column("raw_output", sa.String(), nullable=True))
    op.add_column("review_items", sa.Column("model", sa.String(), nullable=True))


def downgrade() -> None:
    for name in (
        "model",
        "raw_output",
        "source_quotes",
        "validation_errors",
        "is_valid",
        "source_url",
        "scheme_slug",
    ):
        op.drop_column("review_items", name)
