from fastapi.testclient import TestClient

from app.main import app

EXPECTED_ENDPOINTS = {
    ("post", "/households"),
    ("get", "/households/{household_id}"),
    ("patch", "/households/{household_id}"),
    ("delete", "/households/{household_id}"),
    ("post", "/households/{household_id}/members"),
    ("get", "/households/{household_id}/members"),
    ("get", "/households/{household_id}/members/{member_id}"),
    ("patch", "/households/{household_id}/members/{member_id}"),
    ("delete", "/households/{household_id}/members/{member_id}"),
    ("put", "/households/{household_id}/members/{member_id}/documents"),
    ("get", "/schemes"),
    ("get", "/schemes/{slug}"),
}


def test_docs_page_lists_every_endpoint() -> None:
    schema = TestClient(app).get("/openapi.json").json()

    found = {(method, path) for path, ops in schema["paths"].items() for method in ops}
    assert EXPECTED_ENDPOINTS <= found


def test_unexpected_errors_are_a_plain_500_without_details() -> None:
    @app.get("/_test_boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail: postgres://user:password@host")

    try:
        response = TestClient(app, raise_server_exceptions=False).get("/_test_boom")
    finally:
        app.router.routes.pop()  # do not leave the test route in the app

    assert response.status_code == 500
    assert response.json() == {"detail": "Something went wrong on our side."}
    assert "secret" not in response.text


def test_browser_can_send_the_token_header_and_all_methods() -> None:
    from app.config import get_settings

    origin = get_settings().frontend_url
    response = TestClient(app).options(
        "/households",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
