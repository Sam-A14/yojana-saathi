# 003 – Run migrations in the Render start command

## Context
Render's free tier has no shell, so nobody can run `alembic upgrade head` by hand after a deploy.

## Decision
The start command is `alembic upgrade head && uvicorn app.main:app ...`. `/health` does not use
the database. `DATABASE_URL` is optional in settings, and the engine is created on first use.

## Alternatives
- Run migrations inside the FastAPI startup code: hides the step inside the app, and also runs it
  during tests and local `--reload`.
- Run migrations from CI against Neon: needs the database password in GitHub as well, and a deploy
  could go live before the migration finishes.

## Consequences
- A failed migration stops the service from starting, so a broken schema is never served.
- Two instances starting at once could race on a migration. The free tier runs one instance; revisit
  if the service is ever scaled out.
- A slow or paused database delays startup, but not `/health` once the service is up.
- Migrations should stay backward compatible with the previous release, because the old version
  keeps serving until the new one is up.
