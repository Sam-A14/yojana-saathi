# 009 — Eligibility endpoint: ranges, corners and what is listed

## Context
A family gives a birth YEAR and an income BAND, but rules talk about exact age and exact income.
Someone born in 1986 is 39 or 40 today; a household in "2 to 2.5 lakh" earns anywhere in that
range. Picking one number (this year minus birth year, or the band's upper edge) would sometimes
say "eligible" or "not eligible" when the true answer depends on a birthday or a rupee amount we
do not have. The engine must stay unchanged and remain the only decision maker (CLAUDE.md rules 1 and 2).

## Decision
- **Evaluate at the corners.** `app/api/ranges.py` runs the unchanged `evaluate()` at the youngest
  and oldest possible age and at the lowest and highest income, for every combination. If all
  corners give the same status, that is the answer. If they differ, the status is `unknown` and
  `reasons` says why: `depends_on_exact_age` and/or `depends_on_exact_income`. A reason is named
  only if changing that one detail alone changes the answer. The same is done per rule, so a rule
  that depends on the exact age shows up under `unknown_rules` with its own reason.
- **Only ranges the rules read.** If no rule reads `age`, or no rule reads `income_band_max`, that
  dimension is not enumerated. An age inside `any_member` makes every member's age a dimension,
  because another member's age can change the answer (an adult son who paid tax). More than 6
  uncertain ages stops enumerating and returns `unknown` with `depends_on_exact_age`, instead of
  2^n runs or a wrong answer.
- **Age range:** `(today.year - birth_year - 1, today.year - birth_year)`, never below 0. `today`
  comes from a FastAPI dependency (India's date, fixed UTC+5:30), so tests fix the date.
- **Income range:** the band's lower and upper edge, both treated as possible. The top band
  (`above_8_lakh`) has no upper edge, so its upper corner is infinity: a limit above 8 lakh is
  `unknown`, a limit at or below 5 lakh is a definite no. This **replaces** the earlier idea of
  using the upper edge as the income ("conservative-fair"), which could say "eligible" for a family
  that is not.
- **A missing birth year or income band is not a range.** The fact is simply absent and the engine
  says `unknown` itself, with no reason code (the family should be asked, not told it depends).
- **What is returned per member:** `schemes` (eligible, near_miss, unknown) with passed, failed
  and unknown rules, `excluded_by` (nicknames from the failed rules), `missing_documents` and the
  scheme's `verified` flag (false schemes are shown, never hidden). `excluded` lists schemes the
  member would fit except that another person's facts exclude the household (PM-KISAN with a
  taxpaying son), because the family can act on that. `not_eligible_count` counts every other
  definite no, without listing them.
- **Missing documents:** required documents the member answered "no" (`no`) or was not asked about
  (`not_answered`). A document marked `applies_to: household` counts as held if any member has it.
- **A scheme with malformed rules is skipped, logged and named in `skipped_schemes`.** It is never
  turned into an eligibility answer, and one bad scheme does not break the family's page.

## Alternatives
- Age = year - birth_year: wrong by one for part of the year, and wrong in the direction that
  tells a 59-year-old they qualify for a 60+ pension.
- Ask the engine to understand ranges: moves the interesting logic into the file the owner writes and
  explains, and every future operator would need a range version.
- Enumerate every member's age always: up to 2^20 runs per scheme.
- Ask for the exact birth date: more personal data, and still unknown for people who do not know it.

## Consequences
- Near thresholds the answer is `unknown` with a reason the UI can turn into one question
  ("what is the exact age?"). Birth-month questions could narrow the range later.
- Edges are inclusive, so a rule cut exactly at a band edge (for example `lte 100000` with the
  "1 to 2 lakh" band) is `unknown`. This errs towards asking.
- The engine's household/member split is unchanged: `has_<document>` facts are per member, but
  `missing_documents` treats household documents as shared. A household document held by someone
  else can therefore be absent from `missing_documents` while the engine still says `unknown` for a
  member who was not asked. Fix when the setup form decides who answers household documents.
- Cost is small: at most 4 engine runs per member and scheme for today's rules.
