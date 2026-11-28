# 042 – Adding, editing and removing a family member from the dashboard

## Context
Adding a person existed in one place: step 2 of the setup (`/setup/members`). After setup nothing on the
dashboard, the household screen or the menu led there, so a household with only its owner could never grow, and
a one-person household often shows no scheme. Adding people is the point of the product.

## Decision
- **"Add a family member"** under the member cards on the dashboard, with a one-line reason ("We check every
  person in your family against every scheme"). It opens the same form (`MemberForm`) and calls the same API
  (`addMember`), then shows the results again with a note ("Sita was added. Their schemes are below.").
- **Edit and Remove on each card** (`MemberActions`): an icon and a word each, full-size buttons. Edit opens the same form
  with that person's details (fetched when tapped: the results carry only the name). **Remove asks first** ("Remove Sita
  from your family?", "Yes, remove" / "No, keep"), for that person only.
- **One main action.** The form replaces the dashboard while it is open, so its Save is the only main button. On the
  dashboard itself "Add a family member" is the one filled button; the empty-state "Review household details" steps back
  to the outline look (`quiet`), so there is still only one.
- **At 20 people** the button becomes a plain sentence (the same limit as the API and the setup).
- **The example family** has none of these: `MemberResults` shows the buttons only when it is given them.
- **After an add, edit or remove the results are fetched again**: the answer for the whole family can change (one more
  person, or one fewer).
- New words are in English and Hindi; the Hindi is marked for the owner's review.

## Alternatives
- A link from the dashboard to the setup step: reuses everything, but drops the person into "step 2 of 4" of a flow that is finished.
- Edit the card in place: the card is narrow and sits in a grid; a focused form screen is easier to read and to use.
- Remove with no question: one mis-tap would delete a person and their answers.

## Consequences
- A newly added person has unanswered papers and exclusion questions; the usual "Answer this" links on their card lead to
  those screens, so nothing new is needed.
- The Playwright tests use a fake server whose IGNOAPS answer mirrors the two rules; the real engine's answer for the same
  facts is checked in the backend tests.
