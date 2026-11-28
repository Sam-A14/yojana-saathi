# Operations and reference

Everything about running, deploying and maintaining Yojana Saathi: folder map, local setup, the API,
the database, environment variables, deploying to Neon, Render and Vercel, the GitHub workflows that
load and add schemes, and sign-in. The front page of the project is the [README](../README.md).

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
└── .github/workflows/  ci.yml runs on every pull request; seed-database.yml, extract-rules.yml and approve-scheme.yml are run by hand
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

**Sign in with email (no passwords).** `POST /auth/request-code` emails a 6-digit code;
`POST /auth/verify` swaps it for a session token. Send the token on every other call as
`Authorization: Bearer <token>`; it lasts 30 days. A code works for 10 minutes and allows 5 wrong
guesses; one email can ask for 3 codes an hour; and the whole service stops at 80 codes a UTC day
(`EMAIL_DAILY_LIMIT`) to protect the email provider's free quota. Codes are stored only as a keyed
hash and are never logged. Not signed in (or the session expired) gives `401`. Signed in but the
household is not yours, or does not exist, gives `403`. Each person has one household.

| Method and path | Needs sign-in | What it does |
| --- | --- | --- |
| `POST /auth/request-code` | no | Email a sign-in code. Same answer for any address. `429` after 3 an hour, `503` when the day's cap is used. |
| `POST /auth/verify` | no | Swap the emailed code for a session token. |
| `POST /auth/google` | no | Swap a Google ID token for the same session token. Finds or creates the user by lower-case email. `401` for any bad token, `503` if `GOOGLE_CLIENT_ID` is not set. |
| `POST /auth/sign-out` | yes | End this browser's session. |
| `GET /me` | yes | Your email and your household id (null until you set one up). |
| `DELETE /me` | yes | **Delete my data:** the user, their email, and the household, members, documents and results. |
| `POST /households` | yes | Start your household (`409` if you already have one). |
| `GET` / `PATCH /households/{id}` | yes | Read or change the household. |
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

**Sign in with Google.** `POST /auth/google` takes the ID token Google's button gives the page.
The server checks the signature against Google's public keys (the `google-auth` library), then that
the token was made for our own client ID (`GOOGLE_CLIENT_ID`), comes from `accounts.google.com`,
has not expired, and carries a verified email. Then it finds or creates the user by lower-case
email, so Google and email codes reach the same household, and issues the same 30-day session
token. Only the email is kept: never the Google name, photo, id or token. It uses no email codes,
so the per-email and per-day limits do not change. See `docs/decisions/027-google-sign-in.md`.

Rules for what you send: unknown fields are rejected (`422`), so identity numbers cannot be sent;
only birth *year* is stored; a question left as `null` means "not answered", which is different
from "no". Quick try:

```bash
curl -s -X POST localhost:8000/auth/request-code -H 'content-type: application/json' \
  -d '{"email":"you@example.com"}'
```

Locally, set `RESEND_API_KEY` and `AUTH_SECRET` in `backend/.env` (see `.env.example`). Until you
verify a domain with Resend, the code only reaches the email address of your own Resend account.

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
| backend | `AUTH_SECRET` | Long random text (32+ characters) that signs the stored hash of sign-in codes. Never change it once users exist (waiting codes stop working). Never share or log it. |
| backend | `RESEND_API_KEY` | Resend API key, for sending sign-in codes. Never share or log it. |
| backend | `EMAIL_FROM` | Sender shown on the email. Default `Yojana Saathi <onboarding@resend.dev>`, which only reaches your own address. See "Going live with a custom domain". |
| backend | `EMAIL_PROVIDER` | `resend` (default) or `fake` (tests only, sends nothing). |
| backend | `EMAIL_DAILY_LIMIT` | Optional. Most sign-in codes sent per UTC day. Default 80 (Resend's free plan is about 100 a day). |
| backend | `GOOGLE_CLIENT_ID` | Optional. The OAuth client ID for "Continue with Google". Public, not a secret. Unset or empty turns Google sign-in off (`POST /auth/google` answers `503`). See "Sign in with Google". |
| backend | `APP_VERSION` | Optional. Version shown by `/health`. |
| frontend | `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Optional. The same Google OAuth client ID as the backend's `GOOGLE_CLIENT_ID`. Public, not a secret. Missing or empty hides "Continue with Google". Baked in at build time, so redeploy after changing it. Set it for **Production only**: see "Sign in with Google". |
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
   - `AUTH_SECRET` = a long random string, for example the output of
     `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
   - `RESEND_API_KEY` = your key from <https://resend.com> (API Keys). `EMAIL_FROM` is optional
     until you have your own domain.
6. Open `https://<your-service>.onrender.com/health` to check. It does not touch the database, so
   it answers even while Neon is waking up.

The free tier sleeps when idle, so the first request after a break can take about a minute.

### Seed the database (after step 2, and again whenever `data/` changes)

The free Render tier has no shell, so a GitHub Actions workflow loads the data instead. Do the
setup once:

1. In your GitHub repository open Settings > Secrets and variables > Actions > New repository secret.
2. Name: `DATABASE_URL`. Value: the same direct Neon connection string you gave Render. Save.

After that it runs **by itself**: merging a pull request that changes `data/schemes_seed/` or
`data/documents.json` to `main` starts **Seed database**. It first waits (up to 15 minutes) for the
backend deploy to finish its database migrations, then loads the data. A merged scheme is live for
families when that run is green; if it fails, GitHub emails you and the run says why. To run it by
hand: open the Actions tab, choose **Seed database** on the left, click Run workflow, keep branch
`main`, and click the green button. Either way, open the finished run: the "Summary" at the top
lists what was created, updated or left alone.

Notes: the workflow only runs from `main` (it refuses other branches, so unreviewed data cannot
reach production), and it shows up in the Actions list only after the file is on `main`. If it
fails with "DATABASE_URL secret is not set", redo the setup above. The tables must exist first:
Render creates them when the backend starts, so deploy the backend before seeding.

### Add a scheme in one step

Actions > **Add scheme** > Run workflow (branch `main`): type the slug and **either** paste the page text
(the page URL on line 1, then the text exactly as pasted) **or** give one myScheme page address
(`source_url`, like `https://www.myscheme.gov.in/schemes/pmay-g`; not both). With an address the job
reads the site's robots.txt first and refuses if the path is disallowed, opens that one page in headless
Chromium with a User-Agent that names the project, clicks each tab and saves its text, and the pull
request shows the fetched text so you can compare it with the page. It never crawls or follows a link
(see `docs/decisions/049-fetching-a-scheme-page.md`; read the site's terms of use first). It writes `data/scheme_sources/<slug>.txt`,
extracts and validates the rules, and then either opens **one pull request** containing the source
file and the seed file, or, if the proposal failed validation, opens (or adds to) a GitHub issue
that lists the problems. There is no automatic retry. Same one-time setup as the two workflows below
(the `LLM_API_KEY` and `DATABASE_URL` secrets, and "Allow GitHub Actions to create and approve pull
requests"). Read the pull request against `docs/scheme-review-checklist.md`, and **merging it is
the verification**: `approved_by` is whoever started the run, set before anyone read it. The merge
starts **Seed database** by itself. It refuses a slug that already has a source or seed file. The
two workflows below still work for a source file that is already in `data/`.

### Extract scheme rules with the LLM (optional, after seeding)

Paste a scheme's text into `data/scheme_sources/<slug>.txt` (source URL on line 1; see
`data/scheme_sources/README.md`) and merge it to `main`. One-time setup: add a repository secret
`LLM_API_KEY` (a Gemini API key from <https://aistudio.google.com/apikey>); `DATABASE_URL` is the
same secret the seed workflow uses. Then Actions > **Extract scheme rules** > Run workflow > type the
slug. The run summary shows the proposal, whether it passed validation, and the accuracy against
`data/schemes_seed/<slug>.json` if that exists. The proposal is saved to `review_items` as
`pending`; nothing is published. Deploy the backend first so the latest migration has run.

### Approve a scheme proposal (after you have read it)

Turns a proposal you have checked into a pull request, so adding a verified scheme takes one click
plus one review. One-time setup, in the repository settings: Settings > Actions > General >
Workflow permissions > tick **Allow GitHub Actions to create and approve pull requests** and save.
(Without it the last step fails with "GitHub Actions is not permitted to create or approve pull
requests".) The workflow uses the same `DATABASE_URL` secret as the seed workflow.

Then, each time:

1. Read the proposal in the **Extract scheme rules** run summary and note its review item number
   (the "Saved as review item #N" line).
2. Actions > **Approve scheme proposal** > Run workflow, keep branch `main`, type the review item
   number and **your GitHub user name** (it is saved in the file as `approved_by`; the pull request
   also records who ran the workflow).
3. Open the pull request it creates. Read each rule next to its source quote, and the benefit text
   next to its quote. Merge it if they agree. Merging publishes nothing yet.
4. After the merge, run **Seed database**. Only then does the scheme reach families.

It refuses a proposal that did not pass validation, is no longer pending, or whose benefit text has
no stored quote (extract again). If the file would be identical to the one already on `main`, it
says so and opens nothing. Pull requests opened by a workflow do not start the normal CI checks:
close and reopen the pull request to run them (the frontend test that every rule can be shown in
words runs there). The workflow itself already ran the seed-file and test-profile tests.

### Close old review items
Actions tab, **Supersede review items**, type the numbers (for example `2,3,4,5,6,7,8,9,11,12`).
It sets each item that is still *pending* to *rejected* with `reviewed_by` = "superseded by <you>"
(there is no separate "superseded" status). Items that are approved, rejected or missing are left as
they are and listed in the run summary. Nothing is deleted.

### Why is the live site slow? Read the timing

Every request prints one line in the Render logs, and sends the same numbers in a `Server-Timing`
header (browser dev tools > Network > the request > Timing):

```
timing PATCH /households/{household_id} 200 total=921ms db=575ms queries=5 connects=0
```

`total` is the whole request; `db` is the time inside statements; `queries` is how many; `connects` is
how many new database connections it needed (a new one is slow, and happens after the database
slept). Requests over 2 seconds are logged as warnings. Nothing identifying is logged.

`GET /health/db` measures one database round trip from the server right now (`round_trip_ms`) and the
first connection (`first_ms`). A request costs about 10 round trips, so `round_trip_ms` x 10 is roughly
the floor for a save. **Do not use `/health/db` as the uptime ping**: unlike `/health` it wakes the
database and keeps it awake, which uses up the free plan's compute hours.

### 3. Frontend: Vercel

1. On <https://vercel.com>, choose Add New > Project and import this repository.
2. Root directory: `frontend`. Framework: Next.js (detected automatically).
3. Environment variable `NEXT_PUBLIC_API_URL` = your Render address, no trailing slash.
4. Deploy, then copy the Vercel address into `FRONTEND_URL` on Render (step 2.5).

`NEXT_PUBLIC_` values are baked in at build time, so redeploy the frontend after changing it.

## Sign in with Google

Google sign-in costs nothing and needs no domain, so anyone can sign in even while email codes only
reach your own address.

1. In [Google Cloud Console](https://console.cloud.google.com/) create a project, then APIs &
   Services > OAuth consent screen (External; app name, your email), then Credentials > Create
   credentials > OAuth client ID, type **Web application**.
2. Under **Authorized JavaScript origins** add exactly these (no paths, no trailing slash):
   `http://localhost:3000` and `https://yojana-saathi-hazel.vercel.app`. No redirect URIs are needed.
3. Copy the client ID (`...apps.googleusercontent.com`). On Render set `GOOGLE_CLIENT_ID` to it and
   redeploy. On Vercel set `NEXT_PUBLIC_GOOGLE_CLIENT_ID` to the same value and redeploy (it is
   baked in when the site is built). Without it the "Continue with Google" button is hidden.

**Google sign-in only works on `yojana-saathi-hazel.vercel.app` and `localhost`.** Google does not
allow wildcards in Authorized JavaScript origins, so Vercel preview URLs (one new address per
deployment) can never be listed. On a preview the button still appears if the variable is set
there, but Google refuses it ("Error 400: origin_mismatch"); use the email option, or set the
variable for Production only so previews hide the button. If you buy a domain, add it to
the origins too.

While the OAuth consent screen is in "Testing", only the test users you list can sign in. Press
"Publish app" to open it to everyone; the basic email scope needs no Google review.

## Going live with a custom domain

Until you do this, sign-in emails come from Resend's shared test sender
(`onboarding@resend.dev`), which **only delivers to the email address of your own Resend
account**. That is enough to build and test, but no other family can sign in. Moving to your own
domain is a settings change, not a code change.

1. **Buy a domain** from any registrar (a `.in` or `.com` is about ₹500 to 1,000 a year).
2. **Verify it with Resend.** In the Resend dashboard choose Domains > Add Domain and enter it
   (a subdomain such as `mail.yourdomain.in` keeps it away from your website's own mail). Resend
   then shows the exact DNS records to create: normally an SPF `TXT`, a DKIM `TXT`, and an `MX`
   record for bounces. Add them at your registrar's DNS page, exactly as shown, then press Verify.
   It can take from a few minutes to a day. Add the DMARC record Resend suggests too; it helps
   Gmail and Outlook trust the mail.
3. **Change the sender.** On Render set `EMAIL_FROM` to an address on the verified domain, for
   example `Yojana Saathi <login@mail.yourdomain.in>`, and redeploy. Nothing else changes.
4. **Check it** by asking for a code to an address that is not yours, and look in the spam folder
   once.
5. **Point the website at the domain (optional, but people trust it more).** In Vercel open the
   project > Settings > Domains > Add, and enter the domain. Vercel shows the records to create
   at your registrar (an `A` record for the bare domain, a `CNAME` for `www`). Wait until Vercel
   shows the domain as valid.
6. **Tell the backend about the new website address.** On Render set `FRONTEND_URL` to the new
   address (with `https://`, no trailing slash) and redeploy, or the browser will block the
   website's calls to the API (CORS). `NEXT_PUBLIC_API_URL` on Vercel does not change.
