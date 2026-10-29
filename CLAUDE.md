# CLAUDE.md — Yojana Saathi

Yojana Saathi is a free web app: a family sets up its household once, sees every government scheme each member may qualify for, which documents are missing, near-miss schemes, and gets alerts when anything changes. Full plan: `PROJECT_SPEC.md`. Read it before any task.

The owner is a solo student developer building this as a resume project for product-company interviews. They must be able to explain every line. Optimise for clarity over cleverness.

## Non-negotiable rules

1. **The LLM never decides eligibility.** The LLM only extracts rules from scheme text and writes explanations. Every eligibility decision comes from the deterministic rules engine in `backend/app/rules/`.
2. **The owner writes the rules engine.** Do not write or rewrite `backend/app/rules/engine.py` unless the owner explicitly asks in that session. You may write tests, review it, and suggest changes.
3. **Never store identity or financial numbers.** No Aadhaar, PAN, bank account, phone-required flows, or certificate numbers. Documents are stored only as "has / doesn't have".
4. **Never commit secrets.** Config comes from environment variables. Keep `.env.example` files updated with every new variable (names only, no real values).
5. **Do only the task asked.** No extra features, no speculative refactors. Out-of-scope ideas go in the PR description under "Suggestions".

## How to work

- **Plan first.** Start every task by proposing a short plan and the list of files you will create or change. Wait for the owner's OK before writing code.
- **Small PRs.** Aim for changes the owner can review in about 20 minutes. Split bigger tasks.
- **Tests with every change.** Backend: pytest. Frontend: at least type-check and build; Playwright only for the main flows later.
- **Run checks before opening a PR**: `ruff check` and `pytest` in `backend/`; `npm run lint` and `npm run build` in `frontend/`.
- **PR description must include:** What changed · Why · How to test (exact commands or clicks) · **Explain for interview** (3–6 plain-language bullets on the key design choices and trade-offs) · Suggestions (optional).
- **When a design decision is made**, add a short note in `docs/decisions/NNN-title.md` (context, decision, alternatives, consequences).

## Tech standards

- Backend: Python 3.12, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2.0 (typed ORM), Alembic, pytest, ruff. Type hints everywhere.
- Frontend: Next.js (App Router), TypeScript (strict), Tailwind, next-intl for Hindi and English. Mobile-first.
- Database: PostgreSQL. Rules stored as JSONB in versioned rows.
- LLM calls go through one wrapper in `backend/app/llm/` so the provider can be switched.
- Keep functions small and named plainly. Comment the *why*, not the *what*.

## UI text

- Plain words a non-technical parent can follow when read aloud.
- Every eligibility result shows *why* (rules passed or failed) and links to the official source.
- Every result page carries: "Guidance only, not an official decision. Not a government app."
