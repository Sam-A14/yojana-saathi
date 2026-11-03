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
- **Income range:** a band is "more than its lower edge, up to and including its upper edge":
  `1_to_2_lakh` is 100001 to 200000 rupees, `up_to_1_lakh` is 0 to 100000. Incomes are whole
  rupees, so the lowest corner is `lower + 1` and the highest is `upper`. The top band
  (`above_8_lakh`) has no upper edge, so its upper corner is infinity: a limit above 8 lakh is
  `unknown`, a limit at or below 8 lakh is a definite no. This **replaces** the earlier idea of
  using the upper edge as the income ("conservative-fair"), which could say "eligible" for a family
  that is not.
- **Edges give definite answers.** Against `1_to_2_lakh`: a limit of 200000 is eligible, a limit of
  100000 is not eligible (the family earns more than that), and only a limit inside the band, such
  as 150000, is `unknown` with `depends_on_exact_income`. Every rupee belongs to exactly one band.
- **Family-level documents are shared.** `HOUSEHOLD_DOCUMENT_CODES` (`ration_card`, `bpl_card`,
  `family_register`, in `app/rules/values.py`) is the one list. If any member has one of them, every
  member counts as having it, and `shared_documents()` in `facts.py` applies that before the engine
  runs (`has_<code>` becomes true for everyone). `missing_documents` reads the same shared answers,
  so the two cannot disagree. If nobody has it, answers stay as given: "no" stays "no" and a member
  who was not asked stays unanswered. Whether a seed file marks a document `applies_to: household`
  is checked against this list by a test; the list, not the flag, decides sharing.
- **A missing birth year or income band is not a range.** The fact is simply absent and the engine
  says `unknown` itself, with no reason code (the family should be asked, not told it depends).
- **What is returned per member:** `schemes` (eligible, near_miss, unknown) with passed, failed
  and unknown rules, `excluded_by` (nicknames from the failed rules), `missing_documents` and the
  scheme's `verified` flag (false schemes are shown, never hidden). `excluded` lists schemes the
  member would fit except that another person's facts exclude the household (PM-KISAN with a
  taxpaying son), because the family can act on that. `not_eligible_count` counts every other
  definite no, without listing them.
- **Missing documents:** required documents the member answered "no" (`no`) or was not asked about
  (`not_answered`), after family-level documents were shared (above).
- **A scheme with malformed rules is skipped, logged and named in `skipped_schemes`.** It is never
  turned into an eligibility answer, and one bad scheme does not break the family's page.

## Alternatives
- Age = year - birth_year: wrong by one for part of the year, and wrong in the direction that
  tells a 59-year-old they qualify for a 60+ pension.
- Keep both band edges inclusive: a rule cut exactly at an edge was then `unknown`, which asks a
  question the family cannot answer better (they already told us the band).
- Ask the engine to understand ranges: moves the interesting logic into the file the owner writes and
  explains, and every future operator would need a range version.
- Enumerate every member's age always: up to 2^20 runs per scheme.
- Ask for the exact birth date: more personal data, and still unknown for people who do not know it.

## Consequences
- Near thresholds the answer is `unknown` with a reason the UI can turn into one question
  ("what is the exact age?"). Birth-month questions could narrow the range later.
- The engine's household/member split is unchanged: `has_<document>` is still a per-member fact. The
  API layer fills it in with the shared answer, so the mother's IGNWPS result is not `unknown`
  because only the father was asked about the BPL card.
- The hand-labelled profiles 14 and 15 give each person their own BPL answer and feed the engine
  directly, so they still test the engine as written. Through the API the household shares the card,
  so those two profiles have different, hand-worked expectations in `test_eligibility.py`. The
  profile files were not edited (they are ground truth); update their descriptions if you want them
  to match the API's behaviour.
- A family where one member truly has no BPL card but another does is treated as having one. That is
  the intended meaning of a family-level document, but the UI should ask about it once per family.
- Cost is small: at most 4 engine runs per member and scheme for today's rules.
