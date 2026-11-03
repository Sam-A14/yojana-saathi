from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.seed import apply_seed, read_seed_files
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


class Family:
    """A household created through the API, with the headers that open it."""

    def __init__(self, client: TestClient, **fields: Any) -> None:
        response = client.post("/households", json=fields)
        assert response.status_code == 201, response.text
        self.body = response.json()
        self.id: str = self.body["id"]
        self.token: str = self.body["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.url = f"/households/{self.id}"


@pytest.fixture
def make_family(client: TestClient):  # noqa: ANN201
    def make(**fields: Any) -> Family:
        return Family(client, **fields)

    return make
