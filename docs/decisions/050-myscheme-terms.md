# 050 — myScheme's terms: the fetcher is off by default, and every scheme page credits its source

## Context
Decision 049 let the "Add scheme" workflow open a myScheme page itself. It said, in its
consequences, that robots.txt is not permission: a site's terms can forbid automated access that
robots.txt allows, and the code cannot read the terms. The build environment cannot reach
myscheme.gov.in either, so nobody has read its robots.txt, Terms & Conditions or Copyright Policy
for this project. The owner decided to be careful.

## Decision
- **The fetcher refuses every site by default.** `ALLOWED_HOSTS` in `app/pipeline/fetch_page.py`
  is empty, including myscheme.gov.in. A site is allowed only when the owner names it in the
  `FETCH_ALLOWED_HOSTS` repository variable (comma-separated hosts), which the workflow passes to
  the fetch step. With nothing set, the run stops at the fetch step with "Fetching pages is
  switched off", before the browser or the network is used.
- **Pasting the page text still works and is the normal way in.** A person reads a page in their
  own browser and pastes it, as before. Nothing in the pipeline after the fetch step changes.
- **Every scheme page shows its source**: "Source: myScheme (myscheme.gov.in)" when the rules were
  read from a myScheme page, or "Source: Official site (host)" for any other address, linked to
  the scheme version's `source_url`. This is in addition to the "Open the official website" button
  (`official_url`), which can be a different, more official page. The API now sends `source_url`
  on every scheme (it was only on the detail endpoint).
- **README "Data sources and credit"** says where the facts come from, that the app links back and
  does not copy whole pages, and quotes the site's Copyright Policy.

## Alternatives
- Delete the fetcher: it is useful if the owner gets permission, and its tests are the proof that it
  is polite. Switching it off keeps the work and makes the safe state the default.
- Keep it on and rely on robots.txt: rejected, for the reason in 049.
- Credit only in the README: a family reading a scheme page never sees the README, so the credit
  would not be where the data is used.

## Consequences
- To use the fetcher the owner must read the terms, then set `FETCH_ALLOWED_HOSTS` on purpose.
  That is one deliberate act, visible in the repository settings.
- The "Source" line shows the page the rules were read from, which for a pasted scheme is whatever
  URL was on line 1 of the pasted text. A wrong URL there shows as a wrong credit, so the review
  checklist item "`source_url` is the page the rules were read from" matters.
