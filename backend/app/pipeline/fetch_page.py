"""Fetch ONE scheme page politely and save its tabs as a source text file.

    python -m app.pipeline.fetch_page <https://www.myscheme.gov.in/schemes/<slug>> --out <file>

What it does, in this order, and stops at the first refusal:
  1. Only a scheme page on an allowed site (ALLOWED_HOSTS), https, no query or fragment.
  2. Reads the site's robots.txt and refuses if the path is disallowed for this bot, or if
     robots.txt cannot be read (only "does not exist" counts as "no rules"). A Crawl-delay is
     obeyed.
  3. Opens the page in headless Chromium with a User-Agent that names the project, clicks each
     section tab in turn (Details, Benefits, Eligibility, ...) and keeps each tab's visible text.
  4. Writes the text the way a person would paste it: the page URL on line 1, the title, then each
     tab's text under its heading. The "Add scheme" workflow then extracts from that file exactly as
     it does from pasted text.

What it does NOT do: crawl, follow a link, fetch a second page, or send anything but a normal page
load. Page navigation away from the one address is blocked, and images, media and fonts are not
downloaded. One page per run; a person starts every run.
"""

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

PRODUCT = "YojanaSaathiBot"
VERSION = "1.0"

# Only the site whose tab layout this reads. Any other site: paste the text instead.
ALLOWED_HOSTS = frozenset({"www.myscheme.gov.in"})
_PATH = re.compile(r"^/schemes/[a-z0-9]+(?:-[a-z0-9]+)*/?$")

# The tabs of a myScheme page, in the order they are written. Each is also a heading the source
# reader (pipeline/sections.py) knows.
TAB_NAMES = (
    "Details",
    "Benefits",
    "Eligibility",
    "Exclusions",
    "Application Process",
    "Documents Required",
)

MAX_CRAWL_DELAY = 30.0  # seconds; a larger Crawl-delay in robots.txt is capped, not ignored


class FetchError(Exception):
    """The page was not fetched. The message says why, in one line, and what to do instead."""


def user_agent() -> str:
    """Names the project and says what the bot does. Contact details are added only if the owner
    sets FETCH_CONTACT (a URL or address of their choosing); nothing personal is sent by default."""
    agent = (
        f"{PRODUCT}/{VERSION} (student project: reads one scheme page per request, "
        "never crawls, obeys robots.txt)"
    )
    contact = os.environ.get("FETCH_CONTACT", "").strip()
    return f"{agent} {contact}" if contact else agent


# --- 1. which pages --------------------------------------------------------------------------


def check_url(url: str, allowed_hosts: frozenset[str] = ALLOWED_HOSTS) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme != "https" or parts.hostname not in allowed_hosts:
        sites = ", ".join(sorted(allowed_hosts))
        raise FetchError(
            f"Only https pages on {sites} can be fetched. Paste the page text into "
            "'source_text' instead."
        )
    if parts.query or parts.fragment or parts.username or parts.port:
        raise FetchError("Give the plain scheme address, without ?query, #fragment or a port.")
    if not _PATH.fullmatch(parts.path):
        raise FetchError(
            "The address must be one scheme page, like https://www.myscheme.gov.in/schemes/pmay-g."
        )
    return f"https://{parts.hostname}{parts.path.rstrip('/')}"


# --- 2. robots.txt ---------------------------------------------------------------------------


def fetch_robots_txt(origin: str, agent: str, timeout: float = 15.0) -> tuple[int, str]:
    response = httpx.get(
        f"{origin}/robots.txt",
        headers={"User-Agent": agent},
        timeout=timeout,
        follow_redirects=True,
    )
    return response.status_code, response.text


@dataclass(frozen=True)
class Robots:
    crawl_delay: float  # seconds to wait between page actions (0 if robots.txt says nothing)


def check_robots(url: str, agent: str, fetch=fetch_robots_txt) -> Robots:  # noqa: ANN001
    """Refuses (FetchError) unless robots.txt allows this bot to fetch `url`.

    robots.txt that does not exist (404 or 410) means no rules. Anything else that stops us reading
    it (a server error, a timeout, access denied) is a refusal: not knowing is not permission.
    """
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    try:
        status, text = fetch(origin, agent)
    except httpx.HTTPError as error:
        raise FetchError(
            f"Could not read {origin}/robots.txt ({type(error).__name__}), so nothing was fetched. "
            "Try again later, or paste the page text into 'source_text'."
        ) from error
    if status in (404, 410):
        return Robots(crawl_delay=0.0)
    if status != 200:
        raise FetchError(
            f"{origin}/robots.txt answered HTTP {status}, so nothing was fetched. Paste the page "
            "text into 'source_text' instead."
        )
    rules = RobotFileParser()
    rules.parse(text.splitlines())
    if not rules.can_fetch(agent, url):
        raise FetchError(
            f"{origin}/robots.txt does not allow {PRODUCT} to fetch {parts.path}. Nothing was "
            "fetched. Paste the page text into 'source_text' instead."
        )
    delay = rules.crawl_delay(agent)
    return Robots(crawl_delay=min(float(delay), MAX_CRAWL_DELAY) if delay else 0.0)


# --- 3. the page and its tabs ----------------------------------------------------------------


@dataclass(frozen=True)
class FetchedPage:
    url: str
    title: str
    tabs: dict[str, str]  # tab name -> its text, in TAB_NAMES order, only the tabs that exist
    missing: tuple[str, ...]  # tab names the page did not have


def unique_lines(captures: dict[str, list[str]]) -> dict[str, list[str]]:
    """Take away what every tab shows (title, tab bar, share buttons, footer): what is left of each
    capture is that tab's own text. Needs at least two tabs to know what is shared."""
    if len(captures) < 2:
        raise FetchError(
            "Found only one tab, so the page text cannot be told apart from the rest of the page. "
            "Paste the page text into 'source_text' instead."
        )
    shared = set.intersection(*(set(lines) for lines in captures.values()))
    return {
        name: [line for line in lines if line not in shared] for name, lines in captures.items()
    }


def clean_lines(text: str) -> list[str]:
    """Visible text as lines: each trimmed, empty ones dropped."""
    return [" ".join(line.split()) for line in text.splitlines() if line.strip()]


def extract_tabs(
    url: str,
    *,
    agent: str,
    delay: float = 1.5,
    executable_path: str | None = None,
    timeout_ms: int = 45_000,
    tab_names: tuple[str, ...] = TAB_NAMES,
) -> FetchedPage:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    captures: dict[str, list[str]] = {}
    title = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=executable_path, headless=True)
            context = browser.new_context(user_agent=agent, locale="en-IN")
            page = context.new_page()
            page.set_default_timeout(timeout_ms)

            def guard(route):  # noqa: ANN001, ANN202
                request = route.request
                if request.resource_type in ("image", "media", "font"):
                    return route.abort()
                # one page only: leave to a different address is never allowed
                if request.is_navigation_request() and request.url.rstrip("/") != url.rstrip("/"):
                    return route.abort()
                return route.continue_()

            page.route("**/*", guard)
            page.goto(url, wait_until="domcontentloaded")
            _settle(page)
            heading = page.locator("h1").first
            title = " ".join(heading.inner_text().split()) if heading.count() else page.title()

            for name in tab_names:
                tab = _find_tab(page, name)
                if tab is None:
                    continue
                tab.click()
                time.sleep(delay)  # a person's pace, and the site's Crawl-delay
                _settle(page)
                captures[name] = clean_lines(page.locator("body").inner_text())
            browser.close()
    except PlaywrightError as error:
        raise FetchError(
            f"The page could not be opened or read: {str(error).splitlines()[0]}"
        ) from error

    own = unique_lines(captures)
    tabs = {name: "\n".join(own[name]) for name in tab_names if name in own and own[name]}
    if not tabs:
        raise FetchError("The tabs were found but they had no text of their own. Nothing saved.")
    return FetchedPage(
        url=url,
        title=title,
        tabs=tabs,
        missing=tuple(name for name in tab_names if name not in tabs),
    )


def _settle(page) -> None:  # noqa: ANN001
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:  # noqa: BLE001 - a page that never goes quiet is read as it is
        pass


def _find_tab(page, name: str):  # noqa: ANN001, ANN202
    """The clickable tab with this exact label: a tab or a button, never a link (a link could leave
    the page)."""
    for locator in (
        page.get_by_role("tab", name=name, exact=True),
        page.get_by_role("button", name=name, exact=True),
    ):
        if locator.count() > 0:
            return locator.first
    return None


# --- 4. the file -----------------------------------------------------------------------------


def render_source(page: FetchedPage) -> str:
    """The page as a person would paste it: URL on line 1, the title, then each tab under its
    heading."""
    parts = [page.url, "", page.title, ""]
    for name, text in page.tabs.items():
        parts += [name, text, ""]
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch one scheme page's tabs as source text.")
    parser.add_argument("url")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--delay", type=float, default=1.5, help="seconds between tab clicks")
    args = parser.parse_args(argv)

    agent = user_agent()
    try:
        url = check_url(args.url)
        robots = check_robots(url, agent, fetch_robots_txt)  # looked up now, so a test can swap it
        page = extract_tabs(
            url,
            agent=agent,
            delay=max(args.delay, robots.crawl_delay),
            executable_path=os.environ.get("CHROMIUM_PATH") or None,
        )
    except FetchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    args.out.write_text(render_source(page), encoding="utf-8")
    print(f"Fetched {url}", file=sys.stderr)
    for name, text in page.tabs.items():
        print(f"  {name}: {len(text)} characters", file=sys.stderr)
    if page.missing:
        print(f"  not on the page: {', '.join(page.missing)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
