from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Fixed constraint names make migrations deterministic: without them Postgres invents names and
# Alembic cannot reliably drop or alter a constraint later.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Rules and other free-form documents are stored as JSONB (queryable, indexed if ever needed).
    type_annotation_map = {dict[str, Any]: JSONB, datetime: DateTime(timezone=True)}


def created_at_column() -> Mapped[datetime]:
    return mapped_column(server_default=func.now())


def updated_at_column() -> Mapped[datetime]:
    return mapped_column(server_default=func.now(), onupdate=func.now())


def in_list_check(column: str, allowed: tuple[str, ...]) -> str:
    """SQL for a CHECK constraint that limits a text column to a fixed set of values.

    We use CHECK instead of native Postgres enums because adding a value to a native enum is
    awkward in Alembic migrations.
    """
    values = ", ".join(f"'{v}'" for v in allowed)
    return f"{column} IN ({values})"
