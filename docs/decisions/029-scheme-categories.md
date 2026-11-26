# 029 – A fixed list of scheme categories

## Context
`category` on a scheme was a free slug (`^[a-z][a-z0-9_]*$`). The landing page's topic cards were
tied to single hard-coded strings, and Healthcare and Families had none, so they said "Coming soon"
forever. A typo such as `helth` would have been seeded without any error and the card would have
stayed on "Coming soon" with no hint why.

## Decision
- **One list, seven values:** `education`, `health`, `housing`, `family_welfare`, `farmer`,
  `widow_pension`, `pension`. It is an `enum` in `data/scheme.schema.json`, so the seed loader and the
  extractor's validator both reject anything else (and the extractor prompt already carries the schema,
  so the model sees the list).
- **`student` became `education`.** No seed file used `student`. `scholarship` is not a separate
  category: it is a kind of education scheme, not a topic a family looks for.
- **Cards map to categories, not the other way round.** `frontend/lib/categories.ts` holds
  `TOPIC_CATEGORIES`. Families counts `family_welfare` and `housing`; every other card counts one.
  A card shows a count and a link as soon as a seeded scheme has one of its categories. The link opens
  the first of its groups that has a scheme.
- **Two copies, one test.** The schema cannot be imported by the frontend (Vercel builds only
  `frontend/`), so the list is repeated in `categories.ts`. A frontend unit test reads the schema file and
  fails if the lists differ, or if a category has no card, no group, or no words in English or Hindi.
- **TEMPLATE.json** now uses `education` (an enum cannot hold a placeholder). It is still skipped by name
  and still not loaded.

## Alternatives
- Keep free slugs and only fix the cards: cheaper, but typos stay silent.
- Generate `categories.ts` from the schema in a build step: no drift, but a build step to learn and to
  break on Vercel for a list of seven words.
- A `categories` database table: needs a migration and an admin screen for something that changes
  a few times a year.

## Consequences
- Adding a category means editing four things together (schema list, `categories.ts`, the icon map,
  the words in `en.ts` and `hi.ts`); the tests name whichever one was forgotten.
- The Hindi words for the four new categories need a native speaker's review.
- A scheme already in the database with an old category (none today) would still load into the page as
  "Other"; the page never breaks on an unknown value.
