import itertools
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_email_client, get_today
from app.api.security import hash_token, new_token
from app.db.models import Scheme, SchemeVersion, User, UserSession
from app.db.seed import apply_seed, read_seed_files
from app.email import FakeEmailClient
from app.main import app


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """The real app talking to the real test database, inside the per-test rolled-back session."""
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded(db: Session) -> None:
    """The real documents and schemes from data/ (pm-kisan, ignwps)."""
    apply_seed(db, read_seed_files())


def sign_in_user(db: Session, email: str) -> tuple[User, str]:
    """A user with a live session, made directly in the database (the sign-in flow itself is
    tested in test_auth.py). Returns the user and the session token."""
    user = User(email=email)
    db.add(user)
    db.flush()
    token = new_token()
    now = datetime.now(UTC)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=30),
        )
    )
    db.flush()
    return user, token


class Family:
    """A signed-in user and the household they created through the API."""

    def __init__(self, client: TestClient, db: Session, email: str, **fields: Any) -> None:
        self.user, self.token = sign_in_user(db, email)
        self.email = email
        self.headers = {"Authorization": f"Bearer {self.token}"}
        response = client.post("/households", json=fields, headers=self.headers)
        assert response.status_code == 201, response.text
        self.body = response.json()
        self.id: str = self.body["id"]
        self.url = f"/households/{self.id}"


@pytest.fixture
def make_family(client: TestClient, db: Session):  # noqa: ANN201
    counter = itertools.count(1)

    def make(**fields: Any) -> Family:
        return Family(client, db, f"family{next(counter)}@example.com", **fields)

    return make


@pytest.fixture
def signed_in(db: Session) -> dict[str, str]:
    """Headers of a signed-in user who has no household yet."""
    _, token = sign_in_user(db, "newcomer@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mailbox() -> Iterator[FakeEmailClient]:
    """Replaces the email client with one that keeps messages, so tests can read the code."""
    fake = FakeEmailClient()
    app.dependency_overrides[get_email_client] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_email_client, None)


TODAY = date(2026, 11, 3)


@pytest.fixture
def today() -> date:
    """Ages depend on the date, so every eligibility test runs on this fixed day."""
    app.dependency_overrides[get_today] = lambda: TODAY
    return TODAY


def add_scheme(db: Session, slug: str, rules: dict[str, Any]) -> None:
    """A minimal active scheme with the given rules (for rules the seed files do not have)."""
    scheme = Scheme(
        slug=slug,
        name_en=f"Test scheme {slug}",
        level="central",
        category="test",
        official_url="https://example.gov.in",
    )
    db.add(scheme)
    db.flush()
    version = SchemeVersion(
        scheme_id=scheme.id,
        version_no=1,
        rules_json=rules,
        source_url="https://example.gov.in",
    )
    db.add(version)
    db.flush()
    scheme.current_version_id = version.id
    db.flush()
