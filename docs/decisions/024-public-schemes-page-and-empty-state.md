# 024 — A public schemes page, and an empty state for the dashboard

## Context
The home page showed some of the catalogue, but there was no page listing every scheme, and a
family for whom we found nothing saw a summary of zeros and a row of "No schemes found" lines with
no next step.

## Decision
- **`/schemes` is public** (no sign-in, no family data) and lists every scheme from `GET /schemes`,
  grouped by category. It is loaded in the browser, like the home page's cards, so a sleeping
  backend never blocks the page itself (decision 018). A failed load shows a message and "Try again".
- **Only what the API returns is shown** (`SchemeCard`): name (Hindi if there is one), category,
  level and state, the benefit text, the two dates, whether it has been checked, and the official
  link. A missing field is simply not shown, so nothing is invented and an unchecked scheme still
  says "Not yet verified". The same card is used on the home page.
- **The category is shown once:** in the group heading on `/schemes`, and on the card itself on the
  home page, where there are no headings.
- **The dashboard has an empty state.** "Nothing found" means no scheme that may fit, is close,
  needs an answer, or is blocked, for anyone in the family. Schemes that only do not fit are
  counted, not listed, so they do not make the page non-empty. It then shows a plain message, one
  main full-width action ("Review household details", because state, area and income decide what we
  can match) and a quieter one ("See all schemes"). It replaces the summary card and the separate
  "Edit household details" button, so the screen still has one main action.
- **The three count cards stay as they were** (PR B). They are not tappable.

## Alternatives
- **Filters and search on `/schemes`:** more to build and test, and the list is short. Grouping is
  enough for now.
- **Fetching the list on the server:** a faster first paint, but a cold backend would slow or break
  the page, and the call could not be faked in the Playwright tests.
- **Keeping the zeros summary when empty:** "may qualify for 0 schemes" with no next step is a dead end.

## Consequences
- The list is only as complete as the catalogue; the page says "the schemes we check today".
- When a scheme has no Hindi name the English name is shown on the Hindi page.
- All the new Hindi strings are marked "needs native review" in `messages/hi.ts`.
