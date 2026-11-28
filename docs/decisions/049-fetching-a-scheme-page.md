# 049 — Fetching a scheme page (politely, one page, and only after robots.txt)

## Context
Adding a scheme starts with a person copying a myScheme page's tabs into text. That is slow and
error-prone (the pasted tab bar once broke the section reader). The goal is to let the "Add scheme"
workflow open the page itself.

## Decision
- `app/pipeline/fetch_page.py` fetches **one** scheme page and writes it the way a person would
  paste it: the URL on line 1, the title, then each tab's text under its heading.
- **Only `https://www.myscheme.gov.in/schemes/<slug>`** is accepted (no query, fragment, port or
  deeper path). Any other site: paste the text. The tab layout it reads is myScheme's.
- **robots.txt is read first and obeyed.** A disallowed path, a robots.txt that cannot be read (a
  server error, a timeout, access denied) and a failed network call are all refusals; only 404 or
  410 ("no robots.txt") means no rules. A `Crawl-delay` is obeyed (capped at 30 seconds).
- The browser is headless Chromium with a User-Agent that names the project and says what the bot
  does (`YojanaSaathiBot/1.0 (student project: reads one scheme page per request, never crawls,
  obeys robots.txt)`). **No personal details are sent by default**; the owner may add a contact URL
  with the `FETCH_CONTACT` environment variable.
- It never crawls: navigation to any other address is blocked, links are never clicked (a tab must
  be a `tab` or `button`, not a link), images, media and fonts are not downloaded, and there is a
  pause between tab clicks. One page per run, started by a person.
- What each tab shows is found by **taking away what every tab shares** (title, tab bar, share
  buttons, footer), so no knowledge of the page's HTML is needed beyond the tab labels.
- Playwright is in `backend/requirements-fetch.txt`, installed only by the workflow's fetch step.
  The API, Render and the normal CI do not install it; the three browser tests skip without it.

## Alternatives
- Scrape with plain HTTP and BeautifulSoup: myScheme renders its tabs with JavaScript, so the text is
  not in the first response.
- Use myScheme's own API: undocumented; reading it is a bigger step than reading the page a person
  would read, and not obviously allowed.
- Crawl the list of schemes: refused. One page per run keeps the load trivial and the intent clear.

## Consequences
- **robots.txt is not the same as permission.** A site's terms can forbid automated access that
  robots.txt allows. The owner reads the terms of use before enabling this against a site; the code
  cannot read them.
- It cannot be tested against the real site from the build environment (its network does not reach
  myScheme). The tests use a local page with the same tab behaviour. The first real run is the test.
- If myScheme changes its tab labels, a tab is skipped (listed as "not on the page") and the
  validator and the pull request's fetched-text view show what is missing.
