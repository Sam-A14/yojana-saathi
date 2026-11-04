"""/docs can only send the access token if the OpenAPI schema declares a bearer security scheme.

A plain header parameter named "Authorization" is ignored by Swagger UI, which is why the token was
never sent from /docs. These tests pin the declaration so it cannot quietly regress.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    return TestClient(app).get("/openapi.json").json()


def operations(schema: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        (method, path, op)
        for path, item in schema["paths"].items()
        for method, op in item.items()
        if method in HTTP_METHODS
    ]


def test_a_bearer_security_scheme_is_declared(schema: dict[str, Any]) -> None:
    schemes = schema["components"]["securitySchemes"]

    assert list(schemes.values()) == [
        {"type": "http", "scheme": "bearer", "description": schemes["HTTPBearer"]["description"]}
    ]


def test_every_household_endpoint_except_create_requires_it(schema: dict[str, Any]) -> None:
    protected = {
        (method, path)
        for method, path, op in operations(schema)
        if op.get("security") == [{"HTTPBearer": []}]
    }
    expected = {
        (method, path)
        for method, path, _ in operations(schema)
        if path.startswith("/households/")  # the id is in the URL; POST /households has none
    }

    assert expected, "no household endpoints found: the test is looking in the wrong place"
    assert protected == expected


@pytest.mark.parametrize(
    ("method", "path"),
    [("post", "/households"), ("get", "/schemes"), ("get", "/schemes/{slug}"), ("get", "/health")],
)
def test_public_endpoints_do_not_ask_for_a_token(
    schema: dict[str, Any], method: str, path: str
) -> None:
    assert "security" not in schema["paths"][path][method]


def test_there_is_no_authorization_header_parameter_left(schema: dict[str, Any]) -> None:
    # The old approach: Swagger UI silently drops these, so the token was never sent.
    for _, path, op in operations(schema):
        names = {p["name"].lower() for p in op.get("parameters", []) if p["in"] == "header"}
        assert "authorization" not in names, path
