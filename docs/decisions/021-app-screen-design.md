# 021 — Restyling the app screens (PR B of the visual redesign)

## Context
PR A (decision 018) gave the landing page the new look. The setup wizard, sign-in, dashboard,
scheme page and `/example` still used the old plain style (`zinc`/`emerald` classes). They had to
match, without breaking the elder-friendly rules (18px base, nothing under 16px, 48px+ taps, one
main action per screen, a visible Back, a word beside every icon).

Lighthouse on the signed-in screens also reported a 0.145 layout shift. I first guessed the form
swapping in after "Loading…". Measuring with Lighthouse's `layout-shifts` audit showed it was the
**footer**: while a screen shows a short "Loading…", the footer sits on the first screen, and it was
pushed off when the real content arrived. Every signed-in screen had the same 0.145 for that reason.

## Decision
- **Same tokens, no new colours except avatars.** Five soft avatar pairs were added to
  `globals.css` (light and dark), all 7:1 or better. Everything else reuses the existing tokens.
- **Footer shift:** the `(app)` column has `min-h-svh`, so the footer stays below the first
  screen while content loads. One class, measured 0.145 to 0 on the wizard and dashboard (both
  languages). A grey placeholder shaped like a form (`Skeleton`) replaces the one-line "Loading…".
- **Wizard:** a numbered stepper (tick for done) above the same "Step 2 of 4: …" words; member
  cards with initials avatars; each paper as a card with an icon and three answers (Yes / No / Not
  sure), each answer an icon and a word. The answers are still real radio buttons in a named group,
  so keyboard, screen readers and the existing tests work unchanged.
- **Initials use graphemes,** not `name[0]`: the first character of a Hindi name such as "कृष्णा" is
  two code points, and cutting after the first drops the vowel sign.
- **Dashboard:** a warm summary card (the same sentence as before plus three numbers, each with an
  icon and word), one card per person, one card per scheme with a category icon and a status chip
  (colour + icon + word) and a coloured left edge. Chips and edges repeat what the group heading says.
- **Celebration:** ten small pieces of paper fly out once from the summary icon, only when someone
  may qualify. CSS only (`transform` and `opacity`), decorative (`aria-hidden`). Their base style
  is invisible, so the existing `prefers-reduced-motion` rule (animation off) shows nothing.
  The words stay "may qualify", never "you qualify": this is guidance only.
- **Scheme page:** each block is a card with an icon and heading; rules are a checklist with a
  green tick, red cross or blue question mark in a round badge, and the rule written in words.
- **No new Hindi strings.** The restyle reused existing keys, so nothing new needs native review
  (the whole of `messages/hi.ts` is still a first draft, see its header).

## Alternatives
- **Reserve the height of the first screen with a skeleton only.** Would not have fixed the footer,
  which was the real cause.
- **Hide the footer until content loads.** Hides the "Guidance only" notice, which every page must carry.
- **A JavaScript confetti library.** More bytes on a cheap phone for a decoration; CSS does it.
- **A pressed "scale" effect on the answer buttons.** Tried it: the transformed label painted above
  the invisible radio input and swallowed the click. Removed.

## Consequences
- Short pages (for example "not signed in") have empty space above the footer.
- The rounded white card (`rounded-2xl border bg-surface shadow-card`) is still written out by hand in a few places next to the shared `Card`, because some carry a coloured edge. If more variants appear, fold them into `Card`.
- Lighthouse numbers are lab numbers on a local build, good for before/after, not for real phones.
