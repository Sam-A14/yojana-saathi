# Scheme review checklist

Every point here is a mistake that actually happened while adding a scheme. Read a generated scheme
pull request (the file `data/schemes_seed/<slug>.json`) against this list before merging.
Merging is the verification: after the **Seed database** step the family sees the scheme.

Items marked **(validator)** are already refused by the extraction validator, so a proposal that
reaches a pull request has passed them. They stay on the list for hand-edited files, which the
validator does not see.

## 1. The source

- [ ] `data/scheme_sources/<slug>.txt` is the page text exactly as pasted, with the page URL on
      line 1. Nothing tidied, so quotes can be matched word for word.
- [ ] `official_url` is the **official portal** when the source text gives one (for example an
      "Official guidelines" or scholarship portal link). Otherwise it is the page URL. Never a guess.
- [ ] `source_url` is the page the rules were read from.

## 2. Rules

- [ ] **Rules come only from Details, Eligibility or Exclusions.** A quote from Benefits, FAQ,
      Documents Required or Application Process is not accepted **(validator)**.
- [ ] **Exact spelling of closed-list values**, capitals included: category is `"OBC"`, never
      `"obc"`; levels are `class_9_10`, not `Class 9-10` **(validator)**. Never loosen the validator.
- [ ] **Papers are never rules.** A `has_<paper>` rule is allowed only when the Eligibility section
      itself says the applicant must hold it as a condition **(validator)**.
- [ ] Each rule says what its quote says, **including exceptions** ("except Group D" is encoded
      with the main condition, not dropped).
- [ ] A study-level rule (`current_study_level`) is paired with `is_student`. `class_11_12` is
      included **only if the text says Class 11 or 12 students can apply**.
- [ ] Income limits use the band edges (100000, 200000, 250000, 300000, 500000, 800000). "Up to
      Rs. 2 Lakh" is `income_band_max lte 200000`.
- [ ] Nothing is encoded that the app cannot ask the family (a parent's occupation, other
      scholarships held). Those go in `not_checked` (section 5).
- [ ] A rule added or changed **by hand** is recorded in `labeller_notes.notes` with its quote and
      the reason (for example "the page names levels only in the Benefits table"). Section 8.

## 3. Documents

- [ ] Every code exists in `data/documents.json`. A paper with no code is not invented: add the code
      in its own pull request first.
- [ ] **"Any one of" papers are not required.** "Ration card / Aadhaar / Voter ID" are listed with
      `"required": false`. The "any one of" is noted in `labeller_notes`.
- [ ] A **bank passbook** is `bank_account_aadhaar_linked`.
- [ ] Papers appear only in `documents`, **never as lines in `not_checked`**.
- [ ] We store only "has / doesn't have", never a number (Aadhaar, PAN, account, certificate).

## 4. Benefit text

- [ ] `benefit_text_en` says no more than its quote.
- [ ] **Every number in `benefit_text_en` appears in the benefit quote** (validator, from the PR that
      adds the check). Until then, compare each rupee figure with the source by eye.
- [ ] A hand-written benefit text records its quote as `Source quote (benefit_text_en): <words>`
      in `labeller_notes.notes`, copied word for word (whitespace aside). Rows that are not next to
      each other get one note each. A test checks each against the source file.
- [ ] No claim the quotes do not show ("other groups get less" needs those rows quoted).

## 5. "Rules we can't check: ask the office" (`not_checked_en`)

Families read these lines on the scheme page. Each one is:

- [ ] **A plain sentence a parent can read aloud.** No field names (`is_bpl`), no jargon.
- [ ] **A condition only, not a paper and not a step.** "You must be studying at a government
      institute" is a condition. "Bring your fee receipt" is a paper (it goes in `documents`).
      "Register on the portal" is a step (leave it out).
- [ ] Says what the app does not do or where to go: "This app does not check it." or "Ask the office."
- [ ] Covers what was left out of the rules on purpose: an income limit that is not encoded, a
      component or category we cannot test, "other scholarships", "age counted on 1 July", "subject
      to the budget", and Class 11 or 12 when the page does not say.

Good: "Payment depends on the government's budget each year."
Bad: "The applicant must provide a student bank passbook." (a paper)

## 6. Hindi (never machine-trusted)

- [ ] `name_hi`, `benefit_text_hi` and `not_checked_hi` are present or deliberately `null`
      (`null` shows the English). `not_checked_hi` has one line for each English line.
- [ ] `labeller_notes.notes` has `NEEDS NATIVE REVIEW (owner): name_hi, benefit_text_hi and
      not_checked_hi.` The owner reads every Hindi line before merging.
- [ ] Numbers and the rupee sign match the English line exactly.

## 7. Basics

- [ ] `slug` equals the file name; `state` and `level` fit (`state` + `UP` for a state scheme);
      `category` is one of the allowed topics.
- [ ] `verified_at` and `approved_by` are set by the workflow, never typed by the model.
- [ ] Tests pass: `pytest tests/test_seed_files.py tests/test_rules_profiles.py`, then the whole
      backend suite. A new scheme can change counts in end-to-end tests that pin "how many schemes".
- [ ] Sanity run with the real engine: an eligible person is eligible, the next level up or down is
      not, and a missing answer is **unknown**, not "no".

## 8. What to write in `labeller_notes`

Notes are for people and never reach the database. Record:

- what was **added or changed by hand** and why, with the quote;
- the **"any one of"** papers;
- the benefit quotes (section 4);
- the Hindi review line (section 6);
- what is **not encoded** and why (the technical version of `not_checked`).

## 9. The pull request

- [ ] The description starts with a short **"For the owner"** summary: what was changed by hand, the
      Hindi lines to check, and anything uncertain.
- [ ] A reviewer who is not the owner (or an assistant) has **not** compared the rules with the
      official page. The pull request says so. Verification happens when the owner merges.

---

# Adding a scheme: the process

1. **Owner:** pastes the source text (page URL on its first line) and names the scheme. (Giving a
   myScheme page address works only if the owner has switched fetching on with the
   `FETCH_ALLOWED_HOSTS` variable; it is off by default, decision 050.) When the workflow fetched the
   page, the pull request shows the fetched text: **compare it with the page** before merging.
2. **Assistant:** triggers the **Add scheme** workflow with the slug and the text. The workflow
   writes `data/scheme_sources/<slug>.txt`, extracts, validates and, if valid, opens one pull
   request with the source file and the seed file. If the proposal is invalid it opens or updates
   a GitHub issue with the problems. It does not retry: a repeated failure means the prompt or the
   source needs a person.
3. **Assistant:** reads the pull request against this checklist, fixes what is wrong **on the pull
   request's branch** (hand edits recorded as in section 8), runs the tests and puts the "For the
   owner" summary at the top. The assistant never merges.
4. **Owner:** reviews the Hindi and the diff, then clicks **Merge**.
5. **Automatic:** the push to `main` runs **Seed database**, which waits for the database
   migrations and loads the data. A scheme is live when that run is green.

Until the **Add scheme** workflow exists, steps 1 to 2 are: add the source file in a pull request,
run **Extract scheme rules**, then **Approve scheme proposal**.

`approved_by` is the person who started the run. It is set before anyone has read the pull
request, so it means "this person asked for it"; **the merge is the verification**.
