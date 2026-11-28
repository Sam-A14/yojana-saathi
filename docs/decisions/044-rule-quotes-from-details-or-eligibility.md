# 044 — A rule's quote must come from Details or Eligibility

## Context
Every top-level rule needs a quote copied from the source. Until now the quote could be anywhere in
the page. Under "Documents Required" the model found words like "Income certificate of your family"
and "Aadhar card number" and could "prove" an eligibility rule with them (review item 4). Decision
037 already blocked paper rules unless the quote is under Eligibility; other rules were unchecked.
The UP SC/ST Pre Matric page states "Class 9 or 10" under **Details**, not Eligibility, so a rule
about it needs Details to count.

## Decision
When the source has section headings, a rule quote must be under **Details**, **Eligibility** or
**Eligibility Criteria**. A quote that is on the page but under any other heading (Documents
Required, Application Process, Benefits, FAQ, ...) gets the problem `quote_wrong_section`, which
names the heading it was found under. A source with no headings at all (a press release, a PDF) has
no sections to tell apart, so it is still checked against its whole text. The benefit quote is
unchanged: it may come from anywhere, normally Benefits. The extractor prompt says the same.

## Alternatives
- Eligibility only: simpler, but would refuse the Class 9 or 10 condition on the Pre Matric page.
- Refuse sources without headings: safest, but would block a PDF or press release.
- A deny-list (never Documents Required / Application Process): lets any new heading through.

## Consequences
- A real condition written only under Exclusions, Benefits or an FAQ is refused until someone adds
  that heading to `RULE_QUOTE_SECTIONS` (one line in `pipeline/sections.py`). Refusing is the safe
  direction: the reviewer sees the reason and the condition goes in `not_encoded`.
- A paper rule quoted from Documents Required now shows two problems (wrong section, and "papers go
  in documents"), each naming a different fix.
