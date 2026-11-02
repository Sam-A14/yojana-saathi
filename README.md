# Yojana Saathi

Set up your family once. Yojana Saathi shows every government scheme each member may qualify for,
which documents are missing, which schemes are a near miss, and alerts you when anything changes.
Free, in Hindi and English.

> Guidance only, not an official decision. Not a government app.

Status: skeleton, database layer (tables and migrations), and scheme data format with a seed loader. The full plan is in [`PROJECT_SPEC.md`](PROJECT_SPEC.md); working
rules are in [`CLAUDE.md`](CLAUDE.md).

## Folder structure

```
yojana-saathi/
├── backend/            FastAPI app (Python 3.12)
│   ├── app/            main.py (routes, CORS), config.py (settings from env)
│   │   └── db/         SQLAlchemy models (db/models/), engine and session, seed.py (seed loader)
│   ├── alembic/        database migrations (versions/0001_initial_schema.py)
│   ├── tests/          pytest tests (database tests need PostgreSQL)
│   ├── requirements.txt
│   └── .env.example
├── frontend/           Next.js (App Router, TypeScript, Tailwind)
│   ├── app/            pages and layout
│   └── .env.example
├── data/               hand-labelled data: documents.json, scheme JSON Schema, schemes_seed/
│                       (see data/README.md for how to label a scheme)
├── docs/decisions/     one short note per design decision
└── .github/workflows/  ci.yml runs on every pull request; seed-database.yml is run by hand
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

### 3. Frontend: Vercel

1. On <https://vercel.com>, choose Add New > Project and import this repository.
2. Root directory: `frontend`. Framework: Next.js (detected automatically).
3. Environment variable `NEXT_PUBLIC_API_URL` = your Render address, no trailing slash.
4. Deploy, then copy the Vercel address into `FRONTEND_URL` on Render (step 2.5).

`NEXT_PUBLIC_` values are baked in at build time, so redeploy the frontend after changing it.
