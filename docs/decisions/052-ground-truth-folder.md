# 052 — The accuracy score reads `data/ground_truth/`, not the seed files

## Context
The accuracy command scores a proposal against "the hand-labelled seed file". That worked while the
seed files were the hand-labelled ones. Now a seed file can be replaced by a reviewed LLM proposal
(`bump_version`, decision 047), and most seed files were written by the extractor in the first
place. Scoring the model against a file the model wrote gives a perfect, meaningless score, and
replacing a hand-labelled seed would delete the human reference.

## Decision
- **`data/ground_truth/<slug>.json`** holds the copies of files a person labelled by hand
  (today `pm-kisan` and `ignwps`). They have the same shape as a seed file.
- **The accuracy command and the Extract report read only that folder.** A scheme with no file
  there has no score, even if it has a seed file. There is no fall-back to the seed file.
- **Nothing in the pipeline writes to it.** The seed loader (`read_seed_files`) reads
  `data/schemes_seed/` only, so ground truth is never published to families.
- A test pins that the score is still computed from the ground-truth file after the seed file is
  replaced, and that every ground-truth file is named by its slug.

## Alternatives
- Keep scoring against the seed file: the reference disappears on the first `bump_version`.
- Fall back to the seed file when no ground truth exists: that is the meaningless model-vs-model
  score again.
- Keep the reference in git history only: no way to run the score.

## Consequences
- Two copies of the same rules exist until a seed is replaced; they are allowed to differ afterwards.
  The ground-truth copy is the one to trust for "what a person decided".
- A ground-truth file is added by hand, in a pull request, when a person labels a scheme.
- Only two schemes have a score today. The scores say "agrees with the human file", and the labelled
  files themselves have `verified_at: null`, so they are a reference, not a proof.
