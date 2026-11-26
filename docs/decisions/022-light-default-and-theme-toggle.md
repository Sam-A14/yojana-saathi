# 022 — Light by default, with a Light / Dark / Match device toggle

> Colour values superseded in part by [026](026-portal-redesign.md). The toggle, the storage key and the light default are unchanged. On a phone the toggle now sits inside the Menu.

## Context
Decision 018 let the phone decide: dark colours switched on whenever the device was set to dark, and
a manual switch was "not asked for". Two things changed. The product is warm and light on purpose
(the landing page, the avatars, the status colours were all tuned on cream), and a parent who never
chose dark should not meet a dark app because a child once set the phone to dark. People also asked
to choose for themselves.

## Decision
- **Light is the default for everyone**, whatever the device setting.
- **A three-way toggle in the header, next to A / A+ and the language switch:** Light, Dark, Match
  device. Each option is an icon and a word, 48px tall. On a phone it takes its own row, because
  three words do not fit beside the other two controls at 360px.
- **The choice is stored in `localStorage`** (`yojana.theme`, always inside try/catch) and applied
  by a small script in `<head>` before the first paint, like the text size, so the page never
  flashes the wrong colours. Nothing saved, a stale value, or blocked storage all mean Light. With
  storage blocked the toggle still works for that visit; it is just not remembered.
- **It is an attribute, not a class:** `data-theme="light" | "dark" | "device"` on `<html>`. The
  server renders `data-theme="light"`, so a visit without JavaScript is light too.
- **Dark colours are written twice in `globals.css`:** under `data-theme="dark"` and under
  `data-theme="device"` inside a `prefers-color-scheme: dark` media query. A unit test
  (`tests/unit/theme-tokens.spec.ts`) fails if the copies differ or a colour token has no dark
  value. No colour was added or changed, so the contrast measurements of decision 018 still hold.
- **`color-scheme`** is set with the theme, so native controls and scrollbars match.

## Alternatives
- **CSS `light-dark()`:** one copy of each colour, but it needs Chrome 123 (2024). On an older
  Android WebView every token would be invalid and the page would lose its colours. Not worth the
  risk for these users; the duplication is guarded by a test instead.
- **A single button that cycles through the three:** one small control, but a person cannot see
  what the choices are, and cycling is hard to use for older people.
- **A menu behind an icon:** an extra tap, and an icon alone breaks the "word beside every icon" rule.
- **Keeping device-follows-by-default:** the old behaviour; rejected for the reasons above.

## Consequences
- **Behaviour change:** people whose phone is set to dark used to get a dark app and now get a light
  one until they choose "Match device". The choice is one tap and is remembered.
- The header is taller on phones (one more row). The controls stay in the header so they are always
  in the same place.
- `messages/hi.ts` has three new Hindi labels, marked "needs native review".
