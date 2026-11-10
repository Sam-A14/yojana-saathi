"""Sign-in: one-time codes sent by email, and the sessions they open."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, in_list_check
from app.db.models.family import LANGUAGES


class LoginCode(Base):
    """A 6-digit code we emailed. Only a keyed hash of it is stored, never the code itself.

    Times are always passed in by the caller (never the database clock) so tests can move time.
    """

    __tablename__ = "login_codes"
    __table_args__ = (
        CheckConstraint(in_list_check("language", LANGUAGES), name="language_valid"),
        CheckConstraint("attempts >= 0", name="attempts_not_negative"),
        # Both limits ask "how many codes for this email since...?"
        Index("ix_login_codes_email_created_at", "email", "created_at"),
        Index("ix_login_codes_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Plain text on purpose: there is no user row yet when the first code is sent.
    email: Mapped[str]
    code_hash: Mapped[str]
    language: Mapped[str] = mapped_column(default="en")
    attempts: Mapped[int] = mapped_column(default=0)  # wrong guesses so far
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    created_at: Mapped[datetime]


class UserSession(Base):
    """A signed-in browser. The token itself is never stored, only its SHA-256 hash."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]
