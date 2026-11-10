# 018 — Visual design system: tokens, fonts, icons, text size

## Context
The first UI worked but was plain. The main users are a family's "digital helper" and the parents
and grandparents they set it up for, often on a cheap Android phone and slow data. So the look has
to be warm and trustworthy, easy for older eyes, and light to download.

## Decision
- **Tokens, not colours.** Every colour is a CSS variable in `app/globals.css` (cream page, white
  cards, deep green `--primary`, marigold `--accent`, four result-state pairs). Tailwind classes
  read them (`bg-surface`, `text-muted`, `bg-ok-bg`). Dark mode redefines the same variables
  under `prefers-color-scheme`, so components carry no `dark:` classes.
- **Contrast measured, not guessed.** Body and helper text are 7:1 or better (AAA) in both themes;
  button, chip and link text is 4.5:1 or better (AA, most pairs are over 7:1). White text on
  marigold is only 2.2:1, so marigold buttons use dark text. Marigold as text uses `--accent-ink`.
- **Elder-friendly rules override looks.** 18px base (`html { font-size: 112.5% }`), nothing below
  16px (`--text-xs` and `--text-sm` are redefined to 0.9rem), 56px buttons, 48px minimum tap targets.
  An "A / A+" button sets `data-text-size="large"` on `<html>` (21px base). All sizes are in `rem`,
  so everything grows together. The saved choice lives in `localStorage` (inside try/catch) and a
  six-line script in `<head>` applies it before first paint, so the page never jumps.
- **Fonts:** Plus Jakarta Sans (one variable file, headings at 800) and Noto Sans Devanagari, both
  through `next/font` (self-hosted, `display: swap`). The Devanagari font is not preloaded; the
  browser fetches it only if a page shows Hindi letters, so English readers never download it.
- **Icons:** `lucide-react`, named imports only, all in `components/icons.tsx` (which picture means
  which document, category or result state). They are decorative: a word is always next to them.
- **Motion:** CSS only (`float`, `glow`, `rise`), on `transform` and `opacity`. One rule in
  `globals.css` switches all animation and transition off under `prefers-reduced-motion`.
- **Layout:** the home page is full-width (dark green hero, then warm light sections). The setup,
  dashboard and scheme screens moved into the route group `app/(app)/` which gives them the narrow
  column; URLs did not change.
- **Landing scheme cards load in the browser** (`GET /schemes` from a client component), like every
  other call in the app. The backend can take a minute to wake up; the home page must not wait for it.

## Alternatives
- Hand-drawn inline SVG icons: no dependency, but ~35 icons to draw and maintain. `lucide-react`
  is tree-shaken, so only the icons we import are shipped.
- A manual dark/light switch: not asked for; `prefers-color-scheme` covers it.
- Fetching `/schemes` on the server: faster first paint of the cards, but a sleeping backend would
  slow or break the whole home page, and the fetch could not be faked in the Playwright tests.
- Scaling text with the browser's own zoom only: many older users do not know how; a visible button does.

## Consequences
- Pages not yet restyled still carry a few `zinc`/`emerald` classes until PR B moves them to tokens.
- Hindi strings added for the landing page are first drafts ("needs native review" in `messages/hi.ts`).
- The landing copy makes no promise about alerts, because alerts are not built yet.
