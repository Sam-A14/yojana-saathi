# 017 — Editing the household details

## Context
Until now the answers about a home (state, district, area, income, category) could only be given once,
during setup. A result that is "unknown" because one of them was never answered ("not sure") was a
dead end: the screen asked the question but had nowhere to answer it.

## Decision
- `/household/edit` shows the same five questions as the Basics step, filled with the saved answers,
  and saves with `PATCH /households/{id}`. The form is one component (`HouseholdForm`) used by both
  Basics (to create) and this screen (to change), so the two cannot drift apart.
- It sends all five answers every time. Null means "no answer": the API clears the answer, which
  is what "Not sure" means everywhere else (decision 014).
- Linked from the dashboard ("Edit household details") and from every unknown question about the
  home (state, district, area, income, social category), on the dashboard and on the scheme page.
  After saving it goes to the dashboard, which asks for its results again.
- The exact-income reason ("depends on your family's exact income") still has no link: the family
  can only choose a range, so there is nothing they can change that would settle it.

## Alternatives
- Put editing inside the setup wizard: it is a one-way sequence, and "Start a new family" is a
  different action from "change an answer".
- Send only the fields that changed: more code for no gain on five small fields.

## Consequences
- Changing the income range or state can change many results at once. The dashboard is rebuilt from
  the server, so nothing is stale, but nothing warns "this changed 3 results" either.
