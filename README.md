# Yojana Saathi

Set up your family once. Yojana Saathi shows every government scheme each member may qualify for,
which documents are missing, which schemes are a near miss, and alerts you when anything changes.
Free, in Hindi and English.

> Guidance only, not an official decision. Not a government app.

Status: skeleton, database layer (tables and migrations), scheme data format with a seed loader, rules engine, an LLM rule-extraction pipeline (proposals only), and the household, scheme and eligibility API. The full plan is in [`PROJECT_SPEC.md`](PROJECT_SPEC.md); working
rules are in [`CLAUDE.md`](CLAUDE.md).

## Folder structure

```
yojana-saathi/
├── backend/            FastAPI app (Python 3.12)
│   ├── app/            main.py (routes, CORS), config.py (settings from env)
│   │   ├── api/        HTTP endpoints: households, members, documents, schemes; token check
│   │   ├── rules/      rules engine (engine.py), fact names, answer lists (values.py)
│   │   ├── db/         SQLAlchemy models (db/models/), engine and session, seed.py (seed loader)
│   │   ├── llm/        one LLM interface: Gemini implementation, fake for tests, prompts
│   │   └── pipeline/   rule extraction: source text -> LLM -> validator -> review_items; accuracy
│   ├── alembic/        database migrations (versions/0001_initial_schema.py)
│   ├── tests/          pytest tests (database tests need PostgreSQL)
│   ├── requirements.txt
│   └── .env.example
├── frontend/           Next.js (App Router, TypeScript, Tailwind)
│   ├── app/            pages and layout
│   └── .env.example
├── data/               hand-labelled data: documents.json, scheme JSON Schema, schemes_seed/,
│                       scheme_sources/ (scheme text pasted for the LLM)
│                       (see data/README.md for how to label a scheme)
├── docs/decisions/     one short note per design decision
└── .github/workflows/  ci.yml runs on every pull request; seed-database.yml and extract-rules.yml are run by hand
```

More folders (`rules/`, `pipeline/`, `alerts/`, `llm/`) appear as those parts are built.

## Run locally

You need Python 3.12 and Node 22.

Backend (terminal 1):

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API starts without a database. To use one, see "Database" below.

Check it: <http://localhost:8000/health> should show `{"status":"ok","version":"0.1.0"}`.

Frontend (terminal 2):

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

Open <http://localhost:3000>. The page should say "Backend: ok".

## API overview

Start the backend and open <http://localhost:8000/docs> for the full list with a "Try it out" button.
The database must be set up first (see "Database" below).

**No login yet.** `POST /households` returns an `access_token`. Send it on every other household
call as `Authorization: Bearer <token>`. It is shown **once and cannot be recovered**: we store only
a scrambled copy, so if it is lost the household can no longer be opened or deleted. A wrong or
missing token, or an unknown household id, gives `403`.

| Method and path | Needs token | What it does |
| --- | --- | --- |
| `POST /households` | no | Start a household; returns the token. |
| `GET` / `PATCH` / `DELETE /households/{id}` | yes | Read, change, or delete the household and all its members (cascade). |
| `POST` / `GET /households/{id}/members` | yes | Add a member (max 20) / list members. |
| `GET` / `PATCH` / `DELETE /households/{id}/members/{member_id}` | yes | Read, change, remove one member. |
| `PUT /households/{id}/members/{member_id}/documents` | yes | Set which documents a member has (`true`) or does not have (`false`). Replaces the whole set. |
| `GET /households/{id}/eligibility` | yes | Runs the rules engine for every member against every active scheme; see below. |
| `GET /schemes`, `GET /schemes/{slug}` | no | The scheme catalogue. `verified: false` means no human has checked it yet. |

**Eligibility answer.** For each member: `schemes` (status `eligible`, `near_miss` or `unknown`, with
`passed_rules`, `failed_rules`, `unknown_rules`, `excluded_by` and `missing_documents`), `excluded`
(schemes that fit except that another family member's facts exclude the household, with who),
and `not_eligible_count`. Schemes no human has checked come back with `"verified": false`; they are
labelled, not hidden. Only the rules engine decides. The family gives a birth *year* and an income
*band*, so the engine is run for the youngest and oldest possible age and the lowest and highest
income; if the answer changes, the status is `unknown` with `reasons` of `depends_on_exact_age`
and/or `depends_on_exact_income` (see `docs/decisions/009-eligibility-endpoint.md`).

Rules for what you send: unknown fields are rejected (`422`), so identity numbers cannot be sent;
only birth *year* is stored; a question left as `null` means "not answered", which is different
from "no". Quick try:

```bash
curl -s -X POST localhost:8000/households -H 'content-type: application/json' \
  -d '{"state":"UP","area_type":"rural","income_band":"1_to_2_lakh"}'
```

## Database (local)

You need a PostgreSQL 16 server. One way, using Docker:

```bash
docker run -d --name yojana-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
```

Create two databases (one to run the app, one that the tests are free to wipe):

```bash
docker exec yojana-db psql -U postgres -c "CREATE DATABASE yojana;" -c "CREATE DATABASE yojana_test;"
```

In `backend/.env` set `DATABASE_URL` and `TEST_DATABASE_URL` (examples in `.env.example`), then create
the tables:

```bash
cd backend && alembic upgrade head
```

To change a table: edit the model in `app/db/models/`, run `alembic revision --autogenerate -m "what changed"`,
read the generated file in `alembic/versions/`, fix it if needed, and commit it with the model change.
A test fails if the models and migrations disagree.

## Load the seed data (local)

With `DATABASE_URL` set and the tables created (`alembic upgrade head`):

```bash
cd backend && python -m app.db.seed
```

It checks every file in `data/` first, then loads documents and schemes, and prints what changed.
Running it again changes nothing unless a file changed.

## Checks (the same ones CI runs)

```bash
cd backend && ruff check . && pytest
cd frontend && npm run lint && npm run build
```

Without `TEST_DATABASE_URL`, the database tests are skipped (CI refuses to skip them).

## Environment variables

| Where | Name | Meaning |
| --- | --- | --- |
| backend | `FRONTEND_URL` | The one website address allowed to call the API (CORS). |
| backend | `DATABASE_URL` | PostgreSQL connection string. A plain `postgresql://...` URL is fine. Needed for migrations and any database use; not for `/health`. |
| backend | `TEST_DATABASE_URL` | Only for pytest. The database name must end in `_test` because the tests wipe it. |
| backend | `APP_VERSION` | Optional. Version shown by `/health`. |
| frontend | `NEXT_PUBLIC_API_URL` | Where the backend lives. Visible to anyone using the site, so never put secrets in it. |

## Deploy

Do these in order, because each step needs the address from the one before. Free tiers are enough.

### 1. Database: Neon (Postgres)

1. Create a project at <https://neon.tech>.
2. Click Connect and turn **off** "Connection pooling", so you get the direct connection string
   (the host has no `-pooler` in it). Migrations are safer on a direct connection.
3. Copy the string (`postgresql://...`). You will paste it into Render in the next step. Keep it
   secret: it contains the password.

Neon pauses an idle database, so the first query after a break can take a second or two.

### 2. Backend: Render

1. On <https://render.com>, choose New > Web Service and connect this GitHub repository.
2. Root directory: `backend`. Runtime: Python 3. Set the Python version to 3.12 (environment
   variable `PYTHON_VERSION` = `3.12.8`).
3. Build command: `pip install -r requirements.txt`
4. Start command:

   ```bash
   alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

   The free tier has no shell, so the tables are created or updated by this command on every
   start. If a migration fails, the service does not start and the deploy log shows the error.
5. Environment variables:
   - `DATABASE_URL` = the Neon string from step 1.
   - `FRONTEND_URL` = your Vercel address (step 3; set it after you have it, no trailing slash,
     then redeploy).
6. Open `https://<your-service>.onrender.com/health` to check. It does not touch the database, so
   it answers even while Neon is waking up.

The free tier sleeps when idle, so the first request after a break can take about a minute.

### Seed the database (after step 2, and again whenever `data/` changes)

The free Render tier has no shell, so a GitHub Actions workflow loads the data instead. Do the
setup once:

1. In your GitHub repository open Settings > Secrets and variables > Actions > New repository secret.
2. Name: `DATABASE_URL`. Value: the same direct Neon connection string you gave Render. Save.

Then, each time:

1. Open the Actions tab, choose **Seed database** on the left, click Run workflow, keep branch
   `main`, and click the green button.
2. Open the finished run. The "Summary" at the top lists what was created, updated or left alone.

Notes: the workflow only runs from `main` (it refuses other branches, so unreviewed data cannot
reach production), and it shows up in the Actions list only after the file is on `main`. If it
fails with "DATABASE_URL secret is not set", redo the setup above. The tables must exist first:
Render creates them when the backend starts, so deploy the backend before seeding.

### Extract scheme rules with the LLM (optional, after seeding)

Paste a scheme's text into `data/scheme_sources/<slug>.txt` (source URL on line 1; see
`data/scheme_sources/README.md`) and merge it to `main`. One-time setup: add a repository secret
`LLM_API_KEY` (a Gemini API key from <https://aistudio.google.com/apikey>); `DATABASE_URL` is the
same secret the seed workflow uses. Then Actions > **Extract scheme rules** > Run workflow > type the
slug. The run summary shows the proposal, whether it passed validation, and the accuracy against
`data/schemes_seed/<slug>.json` if that exists. The proposal is saved to `review_items` as
`pending`; nothing is published. Deploy the backend first so the latest migration has run.

### 3. Frontend: Vercel

1. On <https://vercel.com>, choose Add New > Project and import this repository.
2. Root directory: `frontend`. Framework: Next.js (detected automatically).
3. Environment variable `NEXT_PUBLIC_API_URL` = your Render address, no trailing slash.
4. Deploy, then copy the Vercel address into `FRONTEND_URL` on Render (step 2.5).

`NEXT_PUBLIC_` values are baked in at build time, so redeploy the frontend after changing it.
