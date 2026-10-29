# 001 – One repository, folders created only when used

## Context
The project has a Python API and a Next.js web app, built by one person. `PROJECT_SPEC.md`
section 9 lists the full target folder tree.

## Decision
Keep backend and frontend in one repository (monorepo). Create only the folders the current
session needs; add `rules/`, `pipeline/`, `alerts/` and the rest in the session that fills them.

## Alternatives
- Two repositories: separate deploys, but changes that touch both sides need two pull requests.
- Create the whole tree now: matches the spec, but git cannot track empty folders, so each would
  need a placeholder file suggesting work that does not exist.

## Consequences
- One pull request can change API and UI together, and one CI file covers both.
- The folder tree grows over time, so `README.md` must be updated as folders are added.
