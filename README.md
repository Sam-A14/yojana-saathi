# Yojana Saathi

Set up your family once. Yojana Saathi shows every government scheme each member may qualify for,
which documents are missing, which schemes are a near miss, and alerts you when anything changes.
Free, in Hindi and English.

> Guidance only, not an official decision. Not a government app.

Status: repository skeleton. The full plan is in [`PROJECT_SPEC.md`](PROJECT_SPEC.md); working
rules are in [`CLAUDE.md`](CLAUDE.md).

## Folder structure

```
yojana-saathi/
├── backend/            FastAPI app (Python 3.12)
│   ├── app/            main.py (routes, CORS), config.py (settings from env)
│   ├── tests/          pytest tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/           Next.js (App Router, TypeScript, Tailwind)
│   ├── app/            pages and layout
│   └── .env.example
├── data/               hand-made scheme and test data (empty for now)
├── docs/decisions/     one short note per design decision
└── .github/workflows/  CI: runs on every pull request
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

Check it: <http://localhost:8000/health> should show `{"status":"ok","version":"0.1.0"}`.

Frontend (terminal 2):

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

Open <http://localhost:3000>. The page should say "Backend: ok".

## Checks (the same ones CI runs)

```bash
cd backend && ruff check . && pytest
cd frontend && npm run lint && npm run build
```

## Environment variables

| Where | Name | Meaning |
| --- | --- | --- |
| backend | `FRONTEND_URL` | The one website address allowed to call the API (CORS). |
| backend | `APP_VERSION` | Optional. Version shown by `/health`. |
| frontend | `NEXT_PUBLIC_API_URL` | Where the backend lives. Visible to anyone using the site, so never put secrets in it. |

## Deploy

Do these in order, because each step needs the address from the one before. Free tiers are enough.

### 1. Database: Neon (Postgres)

Nothing uses the database yet. When it is needed: create a project at <https://neon.tech>, copy
the connection string, and add it to the backend as a new environment variable (the name will be
added to `backend/.env.example` then).

### 2. Backend: Render

1. On <https://render.com>, choose New > Web Service and connect this GitHub repository.
2. Root directory: `backend`. Runtime: Python 3. Set the Python version to 3.12 (environment
   variable `PYTHON_VERSION` = `3.12.8`).
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Environment variable `FRONTEND_URL` = your Vercel address (step 3; set it after you have it,
   no trailing slash, then redeploy).
6. Open `https://<your-service>.onrender.com/health` to check.

The free tier sleeps when idle, so the first request after a break can take about a minute.

### 3. Frontend: Vercel

1. On <https://vercel.com>, choose Add New > Project and import this repository.
2. Root directory: `frontend`. Framework: Next.js (detected automatically).
3. Environment variable `NEXT_PUBLIC_API_URL` = your Render address, no trailing slash.
4. Deploy, then copy the Vercel address into `FRONTEND_URL` on Render (step 2.5).

`NEXT_PUBLIC_` values are baked in at build time, so redeploy the frontend after changing it.
