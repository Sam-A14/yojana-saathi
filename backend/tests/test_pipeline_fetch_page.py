"""Fetching one scheme page politely: which pages, robots.txt, the tabs, and what is never done."""

import os
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from app.pipeline import fetch_page
from app.pipeline.fetch_page import (
    FetchedPage,
    FetchError,
    check_robots,
    check_url,
    render_source,
    unique_lines,
    user_agent,
)
from app.pipeline.sections import split_sections
from app.pipeline.source import read_source

AGENT = user_agent()
GOOD = "https://www.myscheme.gov.in/schemes/pmay-g"


# --- which pages -------------------------------------------------------------------------------


def test_a_myscheme_scheme_page_is_accepted_and_tidied() -> None:
    assert check_url(GOOD) == GOOD
    assert check_url(GOOD + "/") == GOOD
    assert check_url("  https://www.myscheme.gov.in/schemes/up-obc-post-matric  ").endswith(
        "matric"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://www.myscheme.gov.in/schemes/pmay-g",  # not https
        "https://example.com/schemes/pmay-g",  # another site
        "https://myscheme.gov.in/schemes/pmay-g",  # not the exact host
        "https://www.myscheme.gov.in/search?keyword=housing",  # not a scheme page
        "https://www.myscheme.gov.in/schemes",  # the list, not a page
        "https://www.myscheme.gov.in/schemes/pmay-g/extra",  # a deeper path
        "https://www.myscheme.gov.in/schemes/pmay-g?x=1",  # a query
        "https://www.myscheme.gov.in/schemes/pmay-g#details",  # a fragment
        "https://user@www.myscheme.gov.in/schemes/pmay-g",
        "https://www.myscheme.gov.in:8443/schemes/pmay-g",
        "https://www.myscheme.gov.in/schemes/../admin",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "",
    ],
)
def test_anything_else_is_refused_with_the_way_out(url: str) -> None:
    with pytest.raises(FetchError) as error:
        check_url(url)
    assert (
        "source_text" in str(error.value)
        or "scheme address" in str(error.value)
        or "page" in str(error.value)
    )


# --- who we say we are -------------------------------------------------------------------------


def test_the_user_agent_names_the_project_and_says_what_it_does() -> None:
    agent = user_agent()
    assert agent.startswith("YojanaSaathiBot/")
    assert "one scheme page per request" in agent and "never crawls" in agent
    assert "robots.txt" in agent


def test_the_user_agent_carries_nothing_personal_unless_the_owner_adds_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FETCH_CONTACT", raising=False)
    plain = user_agent()
    assert "@" not in plain and "github.com" not in plain and "Sam-A14" not in plain

    monkeypatch.setenv("FETCH_CONTACT", "https://example.org/contact")
    assert user_agent().endswith("https://example.org/contact")


# --- robots.txt --------------------------------------------------------------------------------


def robots(status: int, text: str = ""):  # noqa: ANN201
    return lambda origin, agent: (status, text)


def test_a_page_robots_txt_allows_is_fetched() -> None:
    result = check_robots(GOOD, AGENT, robots(200, "User-agent: *\nDisallow: /admin\n"))
    assert result.crawl_delay == 0.0


def test_a_disallowed_path_is_refused_with_a_clear_message() -> None:
    with pytest.raises(FetchError) as error:
        check_robots(GOOD, AGENT, robots(200, "User-agent: *\nDisallow: /schemes\n"))

    message = str(error.value)
    assert "does not allow YojanaSaathiBot" in message and "/schemes/pmay-g" in message
    assert "Nothing was fetched" in message and "source_text" in message


def test_a_rule_for_our_bot_name_beats_the_general_rule() -> None:
    text = "User-agent: *\nAllow: /\n\nUser-agent: YojanaSaathiBot\nDisallow: /\n"
    with pytest.raises(FetchError):
        check_robots(GOOD, AGENT, robots(200, text))


def test_a_rule_for_another_bot_does_not_bind_us() -> None:
    check_robots(GOOD, AGENT, robots(200, "User-agent: SomeOtherBot\nDisallow: /\n"))


def test_an_empty_robots_txt_allows_everything() -> None:
    check_robots(GOOD, AGENT, robots(200, ""))


@pytest.mark.parametrize("status", [404, 410])
def test_no_robots_txt_means_no_rules(status: int) -> None:
    assert check_robots(GOOD, AGENT, robots(status)).crawl_delay == 0.0


@pytest.mark.parametrize("status", [401, 403, 429, 500, 502, 503])
def test_a_robots_txt_that_cannot_be_read_is_a_refusal_not_permission(status: int) -> None:
    with pytest.raises(FetchError) as error:
        check_robots(GOOD, AGENT, robots(status))
    assert f"HTTP {status}" in str(error.value) and "nothing was fetched" in str(error.value)


def test_a_network_failure_reading_robots_txt_is_a_refusal() -> None:
    def broken(origin: str, agent: str) -> tuple[int, str]:
        raise httpx.ConnectTimeout("slow")

    with pytest.raises(FetchError) as error:
        check_robots(GOOD, AGENT, broken)
    assert "Could not read" in str(error.value) and "ConnectTimeout" in str(error.value)


def test_a_crawl_delay_is_obeyed_but_capped() -> None:
    assert (
        check_robots(GOOD, AGENT, robots(200, "User-agent: *\nCrawl-delay: 4\n")).crawl_delay == 4.0
    )
    capped = check_robots(GOOD, AGENT, robots(200, "User-agent: *\nCrawl-delay: 600\n"))
    assert capped.crawl_delay == fetch_page.MAX_CRAWL_DELAY


def test_robots_txt_is_read_from_the_same_site_with_our_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        seen.update(url=url, **kwargs)
        return httpx.Response(200, text="", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    status, _ = fetch_page.fetch_robots_txt("https://www.myscheme.gov.in", AGENT)

    assert status == 200 and seen["url"] == "https://www.myscheme.gov.in/robots.txt"
    assert seen["headers"] == {"User-Agent": AGENT}


# --- the text of the tabs ----------------------------------------------------------------------


def test_what_every_tab_shows_is_taken_away_and_each_tab_keeps_its_own_text() -> None:
    chrome = ["PMAY-G", "Details", "Benefits", "Eligibility", "Was this helpful?", "Footer"]
    captures = {
        "Details": [*chrome, "About the scheme."],
        "Benefits": [*chrome, "Rs 1,20,000.", "A loan."],
        "Eligibility": [*chrome, "Rural households."],
    }

    assert unique_lines(captures) == {
        "Details": ["About the scheme."],
        "Benefits": ["Rs 1,20,000.", "A loan."],
        "Eligibility": ["Rural households."],
    }


def test_one_tab_alone_cannot_be_told_apart_from_the_page() -> None:
    with pytest.raises(FetchError, match="only one tab"):
        unique_lines({"Details": ["a", "b"]})


def test_the_source_text_is_laid_out_like_a_pasted_page() -> None:
    page = FetchedPage(
        url=GOOD,
        title="Pradhan Mantri Awaas Yojana - Gramin",
        tabs={"Details": "About it.", "Eligibility": "Rural households.\nNo vehicle."},
        missing=("Benefits", "Exclusions", "Application Process", "Documents Required"),
    )

    text = render_source(page)

    assert text.splitlines()[0] == GOOD  # the URL on line 1
    assert text.endswith("\n")
    assert split_sections(text) == {
        "details": "About it.\n",
        "eligibility": "Rural households.\nNo vehicle.",
    }


def test_the_written_file_is_read_by_the_normal_source_reader(tmp_path: Path) -> None:
    page = FetchedPage(url=GOOD, title="A title", tabs={"Details": "Text here."}, missing=())
    folder = tmp_path / "scheme_sources"
    folder.mkdir()
    (folder / "pmay-g.txt").write_text(render_source(page), encoding="utf-8")

    document = read_source("pmay-g", tmp_path)

    assert document.url == GOOD and "Text here." in document.text


# --- the command: refusals happen before anything is opened --------------------------------------


def test_the_command_refuses_a_bad_address_without_fetching_anything(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("must not reach the network or the browser")

    monkeypatch.setattr(fetch_page, "fetch_robots_txt", boom)
    monkeypatch.setattr(fetch_page, "extract_tabs", boom)
    out = tmp_path / "out.txt"

    assert fetch_page.main(["https://example.com/schemes/x", "--out", str(out)]) == 1

    assert "Only https pages on www.myscheme.gov.in" in capsys.readouterr().err
    assert not out.exists()


def test_the_command_stops_at_robots_txt_before_opening_the_page(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        fetch_page, "fetch_robots_txt", robots(200, "User-agent: *\nDisallow: /schemes/\n")
    )

    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("the browser must not start when robots.txt says no")

    monkeypatch.setattr(fetch_page, "extract_tabs", boom)
    out = tmp_path / "out.txt"

    assert fetch_page.main([GOOD, "--out", str(out)]) == 1

    assert "does not allow YojanaSaathiBot" in capsys.readouterr().err
    assert not out.exists()


# --- the real browser, against a local page that behaves like a tabbed scheme page --------------

PAGE = """<!doctype html><html><head><title>Test scheme | myScheme</title></head><body>
<header><h1>Test Scheme</h1><nav><a href="/other">Other scheme</a></nav></header>
<div role="tablist">
  <button role="tab" onclick="show('d')">Details</button>
  <button role="tab" onclick="show('b')">Benefits</button>
  <button role="tab" onclick="show('e')">Eligibility</button>
  <button role="tab" onclick="show('x')">Exclusions</button>
</div>
<section id="d" class="panel"><p>This is the details text.</p><p>A second paragraph.</p></section>
<section id="b" class="panel" hidden><p>Rs 5,000 a month.</p></section>
<section id="e" class="panel" hidden>
<p>Adult women only.</p><ul><li>Age 18 or more</li></ul></section>
<section id="x" class="panel" hidden><p>Not for tax payers.</p></section>
<footer>Was this helpful? Share</footer>
<script>
function show(id){document.querySelectorAll('.panel').forEach(p=>p.hidden=(p.id!==id));}
</script></body></html>"""


@pytest.fixture
def site() -> Iterator[tuple[str, list[str]]]:
    """A tiny local site. It records every path asked for, so a test can see nothing else was."""
    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            seen.append(self.path)
            body = PAGE.encode() if self.path == "/schemes/test" else b"other page"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:  # keep the test output quiet
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/schemes/test", seen
    finally:
        server.shutdown()


def browser_path() -> str | None:
    return os.environ.get("CHROMIUM_PATH") or None


def fetch_local(url: str) -> FetchedPage:
    pytest.importorskip("playwright.sync_api")
    try:
        return fetch_page.extract_tabs(url, agent=AGENT, delay=0.05, executable_path=browser_path())
    except FetchError as error:
        if "Executable doesn't exist" in str(error) or "browserType.launch" in str(error):
            pytest.skip("no Chromium for Playwright here (set CHROMIUM_PATH)")
        raise


def test_each_tab_is_clicked_and_keeps_only_its_own_text(site: tuple[str, list[str]]) -> None:
    url, _ = site

    page = fetch_local(url)

    assert page.title == "Test Scheme"
    assert page.tabs == {
        "Details": "This is the details text.\nA second paragraph.",
        "Benefits": "Rs 5,000 a month.",
        "Eligibility": "Adult women only.\nAge 18 or more",
        "Exclusions": "Not for tax payers.",
    }
    assert page.missing == ("Application Process", "Documents Required")
    everything = "\n".join(page.tabs.values())
    assert (
        "Other scheme" not in everything and "Was this helpful" not in everything
    )  # the page's frame


def test_only_the_one_page_is_requested_and_no_link_is_followed(
    site: tuple[str, list[str]],
) -> None:
    url, seen = site

    fetch_local(url)

    assert seen == ["/schemes/test"]  # no /other, no second request


def test_the_saved_text_reads_back_with_its_sections(
    site: tuple[str, list[str]], tmp_path: Path
) -> None:
    page = fetch_local(site[0])
    text = render_source(page)

    sections = split_sections(text)

    assert list(sections) == ["details", "benefits", "eligibility", "exclusions"]
    assert "Adult women only." in sections["eligibility"]
