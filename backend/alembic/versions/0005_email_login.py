"""email login

Sign-in with an emailed one-time code replaces the anonymous access token:
- login_codes: codes we emailed (hashed), with expiry and wrong-guess counter
- sessions: signed-in browsers (token hashed)
- households: every household has an owner (user_id NOT NULL, unique); access_token_hash is gone

Households that only had a token cannot be claimed by anyone, so they are deleted (with their
members, documents and results, by ON DELETE CASCADE). Agreed: they are test data.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-10 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("language IN ('en', 'hi')", name=op.f("ck_login_codes_language_valid")),
        sa.CheckConstraint("attempts >= 0", name=op.f("ck_login_codes_attempts_not_negative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_codes")),
    )
    op.create_index("ix_login_codes_email_created_at", "login_codes", ["email", "created_at"])
    op.create_index("ix_login_codes_created_at", "login_codes", ["created_at"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.execute("DELETE FROM households WHERE user_id IS NULL")
    op.drop_constraint(op.f("ck_households_has_owner"), "households", type_="check")
    op.drop_constraint(op.f("uq_households_access_token_hash"), "households", type_="unique")
    op.drop_column("households", "access_token_hash")
    op.alter_column("households", "user_id", existing_type=sa.Uuid(), nullable=False)
    # The unique constraint has its own index, so the plain one is no longer needed.
    op.drop_index("ix_households_user_id", table_name="households")
    op.create_unique_constraint(op.f("uq_households_user_id"), "households", ["user_id"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_households_user_id"), "households", type_="unique")
    op.create_index("ix_households_user_id", "households", ["user_id"])
    op.alter_column("households", "user_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("households", sa.Column("access_token_hash", sa.String(), nullable=True))
    op.create_unique_constraint(
        op.f("uq_households_access_token_hash"), "households", ["access_token_hash"]
    )
    op.create_check_constraint(
        op.f("ck_households_has_owner"),
        "households",
        "user_id IS NOT NULL OR access_token_hash IS NOT NULL",
    )
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_login_codes_created_at", table_name="login_codes")
    op.drop_index("ix_login_codes_email_created_at", table_name="login_codes")
    op.drop_table("login_codes")
