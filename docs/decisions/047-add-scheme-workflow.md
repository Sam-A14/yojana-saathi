# 047 — One "Add scheme" workflow, with the page text as its input

## Context
Adding a scheme took four hand-offs: a pull request for the source file, **Extract scheme rules**,
**Approve scheme proposal**, then **Seed database**. Two merges were needed (the source, then the
scheme). The aim is: paste the source, review the Hindi and the diff, click Merge.

## Decision
- A new workflow, **Add scheme** (`workflow_dispatch`, main only), takes the slug and the page text
  as inputs. It writes `data/scheme_sources/<slug>.txt`, runs the same extraction and approval code
  as the two older workflows, and opens **one** pull request that contains both files, so there is
  one merge. Seed database then runs by itself on the push (decision 046).
- A proposal that fails validation opens or comments on a GitHub issue ("Add scheme failed
  validation: <slug>") with the problems, and the run fails so it shows red. No pull request is
  opened. The source file is not committed, so the same slug is free to use again.
- **No automatic retry.** A systematic failure (the model writing "obc") repeats on every try, so a
  retry only spends the LLM quota; a chance failure costs one more click.
- `approved_by` is the person who started the run (`github.actor`), not a typed input. The pull
  request begins with a paragraph saying this was set before anyone read it, that nothing was
  compared with the official page by a person, and that **merging is the verification**.
- The logic that is easier to test in Python than in shell lives in `app/pipeline/add_scheme.py`
  (writing the source file, the issue text, the pull request notice) and `extract_cli
  --result-file` (a small JSON file with the review item number, valid or not, and the problems).
  The workflow YAML only connects them.
- It refuses a slug that already has a source or seed file: this flow adds schemes, it never
  overwrites a reviewed one.

## Alternatives
- Keep the slug as the only input and the source in a separate pull request: two merges, and the
  source has to be merged before the workflow can read it, because the workflow refuses unreviewed
  branches.
- Retry the model automatically with the problems fed back: more quota, and it would hide a prompt
  that needs fixing.
- Call the older workflows from this one (reusable workflows): fewer lines, but each older workflow
  would need rewriting, and they still serve the manual path.

## Consequences
- The page text travels in a workflow input (about 65,000 characters at most; a scheme page is a few
  thousand). The GitHub web form shows a one-line box, so the workflow is meant to be started from
  the API, by the assistant or by script, with the pasted text.
- Anyone who can start workflows can create a proposal and a pull request. The database is only
  written by the review item (as before) and not at all by the pull request.
- The older **Extract** and **Approve** workflows stay for a source file that is already in `data/`.
