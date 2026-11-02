"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-02 09:43:14.979812
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_hi", sa.String(), nullable=False),
        sa.Column("how_to_get_en", sa.String(), nullable=True),
        sa.Column("how_to_get_hi", sa.String(), nullable=True),
        sa.Column("official_link", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("code", name=op.f("uq_documents_code")),
    )
    op.create_table(
        "schemes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_hi", sa.String(), nullable=True),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("official_url", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("current_version_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "level = 'central' OR state IS NOT NULL", name=op.f("ck_schemes_state_scheme_has_state")
        ),
        sa.CheckConstraint("level IN ('central', 'state')", name=op.f("ck_schemes_level_valid")),
        sa.CheckConstraint(
            "status IN ('active', 'closed', 'paused', 'merged', 'renamed')",
            name=op.f("ck_schemes_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schemes")),
        sa.UniqueConstraint("slug", name=op.f("uq_schemes_slug")),
    )
    op.create_index(
        "ix_schemes_status_level_state", "schemes", ["status", "level", "state"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("language", sa.String(), server_default="en", nullable=False),
        sa.Column("alert_channel", sa.String(), server_default="email", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("alert_channel IN ('email')", name=op.f("ck_users_alert_channel_valid")),
        sa.CheckConstraint("language IN ('en', 'hi')", name=op.f("ck_users_language_valid")),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_users_email_lowercase")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'skipped')",
            name=op.f("ck_alerts_status_valid"),
        ),
        sa.CheckConstraint(
            "type IN ('deadline', 'new_scheme', 'age_threshold', 'rule_change')",
            name=op.f("ck_alerts_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_alerts_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index(
        "ix_alerts_status_scheduled_for", "alerts", ["status", "scheduled_for"], unique=False
    )
    op.create_index(
        "ix_alerts_user_id_created_at", "alerts", ["user_id", "created_at"], unique=False
    )
    op.create_table(
        "households",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("area_type", sa.String(), nullable=True),
        sa.Column("income_band", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "area_type IN ('rural', 'urban')", name=op.f("ck_households_area_type_valid")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_households_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_households")),
    )
    op.create_index("ix_households_user_id", "households", ["user_id"], unique=False)
    op.create_table(
        "review_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scheme_id", sa.Integer(), nullable=True),
        sa.Column("proposed_rules_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_quote", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name=op.f("ck_review_items_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["scheme_id"],
            ["schemes.id"],
            name=op.f("fk_review_items_scheme_id_schemes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_items")),
    )
    op.create_index(
        "ix_review_items_status_created_at", "review_items", ["status", "created_at"], unique=False
    )
    op.create_table(
        "scheme_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scheme_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("rules_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("benefit_text_en", sa.String(), nullable=True),
        sa.Column("benefit_text_hi", sa.String(), nullable=True),
        sa.Column("deadline_start", sa.Date(), nullable=True),
        sa.Column("deadline_end", sa.Date(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("source_hash", sa.String(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "deadline_end IS NULL OR deadline_start IS NULL OR deadline_end >= deadline_start",
            name=op.f("ck_scheme_versions_deadline_order"),
        ),
        sa.CheckConstraint("version_no >= 1", name=op.f("ck_scheme_versions_version_no_positive")),
        sa.ForeignKeyConstraint(
            ["scheme_id"],
            ["schemes.id"],
            name=op.f("fk_scheme_versions_scheme_id_schemes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheme_versions")),
        sa.UniqueConstraint(
            "scheme_id", "version_no", name=op.f("uq_scheme_versions_scheme_id_version_no")
        ),
    )
    op.create_index(
        "ix_scheme_versions_deadline_end", "scheme_versions", ["deadline_end"], unique=False
    )
    # schemes and scheme_versions point at each other, so this foreign key can only be added
    # once both tables exist (hand-edited; autogenerate puts it inside create_table).
    op.create_foreign_key(
        "fk_schemes_current_version_id_scheme_versions",
        "schemes",
        "scheme_versions",
        ["current_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("nickname", sa.String(), nullable=False),
        sa.Column("relation", sa.String(), nullable=False),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(), nullable=True),
        sa.Column("marital_status", sa.String(), nullable=True),
        sa.Column("occupation", sa.String(), nullable=True),
        sa.Column("education", sa.String(), nullable=True),
        sa.Column("is_student", sa.Boolean(), nullable=True),
        sa.Column("disability", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "gender IN ('male', 'female', 'other')", name=op.f("ck_members_gender_valid")
        ),
        sa.CheckConstraint(
            "birth_year BETWEEN 1900 AND 2100", name=op.f("ck_members_birth_year_range")
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_members_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_members")),
    )
    op.create_index("ix_members_household_id", "members", ["household_id"], unique=False)
    op.create_table(
        "scheme_documents",
        sa.Column("scheme_version_id", sa.Integer(), nullable=False),
        sa.Column("document_code", sa.String(), nullable=False),
        sa.Column("required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("applies_to", sa.String(), server_default="applicant", nullable=False),
        sa.CheckConstraint(
            "applies_to IN ('applicant', 'household')",
            name=op.f("ck_scheme_documents_applies_to_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["document_code"],
            ["documents.code"],
            name=op.f("fk_scheme_documents_document_code_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scheme_version_id"],
            ["scheme_versions.id"],
            name=op.f("fk_scheme_documents_scheme_version_id_scheme_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "scheme_version_id", "document_code", name=op.f("pk_scheme_documents")
        ),
    )
    op.create_index(
        "ix_scheme_documents_document_code", "scheme_documents", ["document_code"], unique=False
    )
    op.create_table(
        "eligibility_results",
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("scheme_version_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "failed_rules_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('eligible', 'near_miss', 'not_eligible', 'unknown')",
            name=op.f("ck_eligibility_results_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            name=op.f("fk_eligibility_results_member_id_members"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scheme_version_id"],
            ["scheme_versions.id"],
            name=op.f("fk_eligibility_results_scheme_version_id_scheme_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "member_id", "scheme_version_id", name=op.f("pk_eligibility_results")
        ),
    )
    op.create_index(
        "ix_eligibility_results_scheme_version_id",
        "eligibility_results",
        ["scheme_version_id"],
        unique=False,
    )
    op.create_table(
        "member_documents",
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("document_code", sa.String(), nullable=False),
        sa.Column("has", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_code"],
            ["documents.code"],
            name=op.f("fk_member_documents_document_code_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            name=op.f("fk_member_documents_member_id_members"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("member_id", "document_code", name=op.f("pk_member_documents")),
    )


def downgrade() -> None:
    op.drop_table("member_documents")
    op.drop_index("ix_eligibility_results_scheme_version_id", table_name="eligibility_results")
    op.drop_table("eligibility_results")
    op.drop_index("ix_scheme_documents_document_code", table_name="scheme_documents")
    op.drop_table("scheme_documents")
    op.drop_index("ix_members_household_id", table_name="members")
    op.drop_table("members")
    op.drop_index("ix_scheme_versions_deadline_end", table_name="scheme_versions")
    op.drop_constraint(
        "fk_schemes_current_version_id_scheme_versions", "schemes", type_="foreignkey"
    )
    op.drop_table("scheme_versions")
    op.drop_index("ix_review_items_status_created_at", table_name="review_items")
    op.drop_table("review_items")
    op.drop_index("ix_households_user_id", table_name="households")
    op.drop_table("households")
    op.drop_index("ix_alerts_user_id_created_at", table_name="alerts")
    op.drop_index("ix_alerts_status_scheduled_for", table_name="alerts")
    op.drop_table("alerts")
    op.drop_table("users")
    op.drop_index("ix_schemes_status_level_state", table_name="schemes")
    op.drop_table("schemes")
    op.drop_table("documents")
