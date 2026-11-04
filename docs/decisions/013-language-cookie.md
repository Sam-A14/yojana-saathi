# 013 — Language is a cookie, and the app opts out of the static shell

## Context
The app is bilingual (English and Hindi) with next-intl. This Next.js project has
`cacheComponents` switched on, under which anything that reads request-time data (such as
`cookies()`) outside a `<Suspense>` boundary fails the build.

## Decision
- The language is a plain `locale` cookie (`hi` means Hindi, anything else English), with a toggle in
  the header. No `/en` or `/hi` in URLs: a private, per-family app gains nothing from language URLs.
- The root layout reads the cookie, so it sets `export const instant = false` (Next's documented way
  to allow a blocking route). Every page is therefore rendered per request instead of prerendered.
  That costs little: each page is a thin shell, and all family data is fetched in the browser
  anyway (the token lives in `localStorage`, so the server never sees it).
- Messages are TypeScript files (`messages/en.ts`, `messages/hi.ts`), not JSON, for two reasons:
  JSON cannot carry the "needs native review" comments for the Hindi draft, and `hi` is typed as
  `typeof en`, so a key missing in Hindi fails type-check. `global.d.ts` also types the keys, so a
  typo in `t("home.titel")` fails type-check.

## Alternatives
- Language in the URL (`app/[locale]/...`, `generateStaticParams`): keeps every page prerendered
  and gives Hindi pages their own links for search engines. It also needs a proxy for the redirect
  and locale-aware links everywhere. Worth revisiting if finding the site through search in Hindi matters.
- Wrapping the cookie read in `<Suspense>`: `<html lang>` cannot sit inside Suspense.
- Turning `cacheComponents` off: not mine to change; it came with the project skeleton.

## Consequences
- No static HTML for the home page; a little more server work per visit.
- Hindi text is an unreviewed first draft (marked in every section of `messages/hi.ts`). A native
  speaker must read every screen before launch.
