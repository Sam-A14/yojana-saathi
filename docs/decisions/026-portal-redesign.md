# 026 — Portal redesign: the last visual pass (PR 1 of 2)

## Context
Decisions 018, 021 and 022 gave the app a cream-and-green look with a dark green hero. The owner chose
a final direction, "modern Indian public-service portal": white and soft ivory backgrounds, deep navy
and muted teal as brand colours, warm gold for highlights. After this pass **the design is frozen**:
later work may fix bugs and add content, not change the look.

## Decision
- **Same token names, new values.** `--primary` is now deep navy, `--accent` is gold, `--teal` is new,
  `--bg` is ivory. Because components read tokens, the whole app (every page) was recoloured in PR 1;
  PR 2 changes layout and structure only. Result-state and avatar colours are unchanged.
- **Gold is never text on ivory or white** (about 2:1). It is a fill with navy text on it, a border, or
  a short bar. Gold-coloured words use `--accent-ink` (a dark bronze).
- **Contrast is a test, not a claim.** `tests/unit/contrast.spec.ts` reads the real colours from
  `globals.css` and fails if any pair drops under its target (7:1 for reading text, 4.5:1 for button,
  chip and link text, 3:1 for input borders), in light and in dark. Key pairs today:

| Pair | Light | Dark |
|---|---|---|
| Body text | 15.8:1 | 16.2:1 |
| Body text on cards | 16.8:1 | 14.4:1 |
| Helper text | 8.1:1 | 10.3:1 |
| Helper text on soft panels | 7.3:1 | 8.3:1 |
| Link / navy text | 11.5:1 | 9.1:1 |
| White on navy button | 12.2:1 | 9.0:1 |
| Teal text | 8.1:1 | 8.9:1 |
| Gold-ink text | 7.5:1 | 10.2:1 |
| Navy on gold fill | 8.7:1 | 10.2:1 |
| Text on navy footer/strip | 15.2:1 | 16.9:1 |
| Muted text on navy | 11.3:1 | 11.9:1 |
| Input border (needs 3) | 3.7:1 | 4.7:1 |

- **Header:** two rows. A top strip always shows A / A+ and the language (the controls older readers
  need most) and, from tablet width, the theme choice. The main row has the logo, the tagline, the pages
  (Home, Schemes, How it works, FAQ, About) and a Sign in button. Below about 1150px (Tailwind breakpoints are in rem, and the root is 18px) the pages and Sign in move
  into a **Menu** button (icon plus word). On a phone the theme choice is inside the Menu.
- **Landing page:** hero (headline, one main button, photo, curved edge) -> topic cards -> how it works
  -> trust strip -> FAQ -> about -> footer. "Who it's for" and "Schemes we check" were removed: the topic
  cards and `/schemes` cover them.
- **Topic cards and honesty.** Six topics map to the categories the backend really has:
  Education = `student`, Agriculture = `farmer`, Women & Family = `widow_pension`, Senior Citizens =
  `pension`. Healthcare and Families have no category yet, so they always read "Coming soon". The number
  on a card is the live count from `GET /schemes`; **a count of 0 reads "Coming soon" and is not a
  link**, so nobody lands on an empty page. If the server cannot be reached, no number is shown at all.
  A card with schemes links to `/schemes#group-<category>`, the group heading that page already has.
- **The seed template never counts.** `data/schemes_seed/TEMPLATE.json` is skipped by file name in
  `backend/app/db/seed.py`, so it is never in the database, on `/schemes` or in a count. Tests now
  cover this three ways: a valid template next to a real scheme in the loader, the committed categories
  (no `replace_with_category`), and the `/schemes` API answer.
- **Trust strip uses only true sentences:** every scheme links to its official source; each scheme shows
  whether and when it was last checked (the date, or "Not yet verified" while no person has checked it,
  today's state of both seeded schemes; reworded in PR 2 so it no longer implies a date is always there); we never ask for Aadhaar numbers and a person can delete their data. We do not claim
  "verified", "always up to date" or "never shared". A test fails if banned phrases appear on the page.
- **Footer on every page:** "an independent student project, not a government website", links to
  `/privacy` and GitHub, and the photo credit. No emblem, no Digital India mark, no official-looking logo.
- **Hero photo:** "Outdoor family portrait with generations in focus" by the Amritdev, Pexels licence.
  2400px wide, under 400 KB; `next/image` serves smaller WebP files (about 60 KB on a phone). No caption,
  quote or testimonial next to it, so it cannot read as these people endorsing the app. It is cropped to
  4:3, which trims only the sides; all four faces stay visible at 360px.
- **Typography:** still Plus Jakarta Sans (headings at 800) and Noto Sans Devanagari. A second display
  font would cost bytes on cheap phones and would not match Hindi.
- **Motion removed:** the floating phone and glowing sun of decision 018 went with the old hero.

## Alternatives
- **Landing-only palette in PR 1:** every other page would look half-finished between the two PRs.
- **All header controls inside the Menu on a phone:** tidier, but hides A / A+ and the language, which the
  elder-friendly rules say must stay easy to find.
- **A `?category=` filter on `/schemes`:** cleaner URLs, but it changes that page, which belongs to PR 2.
- **Preloading the photo (`priority`):** the photo is below the fold on a phone; preloading it made the
  headline's Lighthouse LCP about 150 ms slower.

## Consequences
- Decisions 018 (palette, hero, motion) and 022 (colour values) are superseded in part; their rules about
  contrast, text size, tap targets and the three-way theme toggle still hold.
- Healthcare and Families need a backend category (and schemes) before they can show a count.
- New Hindi strings are first drafts, marked "needs native review" in `messages/hi.ts`.
- Lighthouse lab numbers (mobile, local build) are in the PR description.
