"""Things the system produces: eligibility results, pipeline proposals, and alerts."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_column, in_list_check, updated_at_column

ELIGIBILITY_STATUSES = ("eligible", "near_miss", "not_eligible", "unknown")
REVIEW_STATUSES = ("pending", "approved", "rejected")
ALERT_TYPES = ("deadline", "new_scheme", "age_threshold", "rule_change")
ALERT_STATUSES = ("pending", "sent", "failed", "skipped")


class EligibilityResult(Base):
    """Latest answer for one member and one scheme version (a cache; always recomputable)."""

    __tablename__ = "eligibility_results"
    __table_args__ = (
        CheckConstraint(in_list_check("status", ELIGIBILITY_STATUSES), name="status_valid"),
        # The primary key already serves "all results for a member"; this serves "who is affected
        # by this scheme version?" when rules change and results must be recomputed.
        Index("ix_eligibility_results_scheme_version_id", "scheme_version_id"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), primary_key=True
    )
    # RESTRICT: versions are history and are never deleted while results point at them.
    scheme_version_id: Mapped[int] = mapped_column(
        ForeignKey("scheme_versions.id", ondelete="RESTRICT"), primary_key=True
    )
    status: Mapped[str]
    # Which rules failed; this is what powers the "why" and the near-miss explanation.
    failed_rules_json: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    computed_at: Mapped[datetime] = updated_at_column()


class ReviewItem(Base):
    """A rule proposal from the pipeline, waiting for a human to approve or reject it."""

    __tablename__ = "review_items"
    __table_args__ = (
        CheckConstraint(in_list_check("status", REVIEW_STATUSES), name="status_valid"),
        Index("ix_review_items_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # NULL when the proposal is for a scheme we do not have yet.
    scheme_id: Mapped[int | None] = mapped_column(ForeignKey("schemes.id", ondelete="RESTRICT"))
    proposed_rules_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source_quote: Mapped[str | None]
    status: Mapped[str] = mapped_column(server_default="pending")
    reviewed_by: Mapped[str | None]
    created_at: Mapped[datetime] = created_at_column()
    reviewed_at: Mapped[datetime | None]


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(in_list_check("type", ALERT_TYPES), name="type_valid"),
        CheckConstraint(in_list_check("status", ALERT_STATUSES), name="status_valid"),
        Index("ix_alerts_user_id_created_at", "user_id", "created_at"),
        # The scheduler's question: "which alerts are pending and due now?"
        Index("ix_alerts_status_scheduled_for", "status", "scheduled_for"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="pending")
    # What the alert is about (scheme, member, deadline); kept loose until the alert code exists.
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    scheduled_for: Mapped[datetime]
    sent_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created_at_column()
