"""member eligibility fields

Adds the member facts that exclusion rules need (PM-KISAN and similar). All columns are nullable:
an unanswered question must stay different from "no".

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-02 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BOOLEAN_COLUMNS = (
    "owns_cultivable_land",
    "paid_income_tax_last_year",
    "is_registered_professional",
    "holds_constitutional_post",
    "is_remarried",
)


def upgrade() -> None:
    for name in BOOLEAN_COLUMNS:
        op.add_column("members", sa.Column(name, sa.Boolean(), nullable=True))
    op.add_column("members", sa.Column("govt_employee", sa.String(), nullable=True))
    op.add_column("members", sa.Column("pension_band", sa.String(), nullable=True))
    op.create_check_constraint(
        op.f("ck_members_govt_employee_valid"),
        "members",
        "govt_employee IN ('none', 'group_d', 'other')",
    )
    op.create_check_constraint(
        op.f("ck_members_pension_band_valid"),
        "members",
        "pension_band IN ('none', 'below_10k', '10k_plus')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_members_pension_band_valid"), "members", type_="check")
    op.drop_constraint(op.f("ck_members_govt_employee_valid"), "members", type_="check")
    op.drop_column("members", "pension_band")
    op.drop_column("members", "govt_employee")
    for name in reversed(BOOLEAN_COLUMNS):
        op.drop_column("members", name)
