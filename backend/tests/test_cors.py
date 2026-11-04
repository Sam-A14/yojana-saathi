import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings, vercel_preview_regex
from app.main import add_cors

PROJECT = "yojana-saathi"
TEAM = "samriddhisrivastava1401-6163s-projects"
PRODUCTION = "https://yojana-saathi.example"

# Real deployment URLs (one per deployment) and the per-branch form.
ALLOWED_PREVIEWS = [
    f"https://{PROJECT}-meku7tj1r-{TEAM}.vercel.app",
    f"https://{PROJECT}-fxh7f7ksi-{TEAM}.vercel.app",
    f"https://{PROJECT}-git-claude-frontend-setup-{TEAM}.vercel.app",
    f"https://{PROJECT}-git-main-{TEAM}.vercel.app",
]
REFUSED = [
    # Another project or another team on Vercel.
    f"https://other-app-meku7tj1r-{TEAM}.vercel.app",
    f"https://{PROJECT}-meku7tj1r-someone-elses-projects.vercel.app",
    # Not https, wrong host, or extra text before/after (the regex is anchored at both ends).
    f"http://{PROJECT}-meku7tj1r-{TEAM}.vercel.app",
    f"https://{PROJECT}-meku7tj1r-{TEAM}.vercel.app.evil.example",
    f"https://evil.example/https://{PROJECT}-meku7tj1r-{TEAM}.vercel.app",
    f"https://{PROJECT}-meku7tj1r-{TEAM}.vercel.app:8080",
    f"https://{PROJECT}-meku7tj1r-{TEAM}.vercelXapp",
    # A dot where the slug has none: re.escape must stop it acting as "any character".
    "https://yojana-saathi-meku7tj1r-samriddhisrivastava1401-6163s-projectsXvercel.app",
    # The project's own name with nothing between project and team.
    f"https://{PROJECT}-{TEAM}.vercel.app",
]


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    add_cors(app, Settings(frontend_url=PRODUCTION, vercel_project=PROJECT, vercel_team=TEAM))

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "yes"}

    return TestClient(app)


@pytest.mark.parametrize("origin", ALLOWED_PREVIEWS)
def test_preview_origins_are_allowed(client: TestClient, origin: str) -> None:
    response = client.get("/ping", headers={"Origin": origin})

    assert response.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", REFUSED)
def test_lookalike_origins_are_refused(client: TestClient, origin: str) -> None:
    response = client.get("/ping", headers={"Origin": origin})

    assert "access-control-allow-origin" not in response.headers


def test_production_origin_still_works(client: TestClient) -> None:
    response = client.get("/ping", headers={"Origin": PRODUCTION})

    assert response.headers["access-control-allow-origin"] == PRODUCTION


def test_browser_preflight_from_a_preview_may_send_the_token_header(client: TestClient) -> None:
    origin = ALLOWED_PREVIEWS[0]
    response = client.options(
        "/ping",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "Authorization" in response.headers["access-control-allow-headers"]


def test_without_vercel_settings_only_production_is_allowed() -> None:
    app = FastAPI()
    add_cors(app, Settings(frontend_url=PRODUCTION, _env_file=None))
    response = TestClient(app).get("/", headers={"Origin": ALLOWED_PREVIEWS[0]})

    assert "access-control-allow-origin" not in response.headers


def test_the_regex_is_anchored_at_both_ends() -> None:
    pattern = vercel_preview_regex(PROJECT, TEAM)

    assert pattern.startswith("^") and pattern.endswith("$")
    assert re.fullmatch(pattern, ALLOWED_PREVIEWS[0])


@pytest.mark.parametrize("only", [{"vercel_project": PROJECT}, {"vercel_team": TEAM}])
def test_setting_only_one_vercel_slug_is_an_error(only: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="both VERCEL_PROJECT and VERCEL_TEAM"):
        Settings(_env_file=None, **only)


def test_blank_vercel_slugs_mean_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_PROJECT", "")
    monkeypatch.setenv("VERCEL_TEAM", " ")

    assert Settings(_env_file=None).frontend_preview_regex is None
