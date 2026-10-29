# PROJECT_SPEC.md — Yojana Saathi

## 1. Product

**One line:** One person sets up their whole household once; the app shows every scheme each member may qualify for, which documents are missing, what they are close to qualifying for, and alerts them when anything changes.

**Core bet:** families miss benefits because nobody re-checks when life changes, documents are missing, and deadlines pass. Discovery exists (myScheme); follow-through does not.

**Positioning:** myScheme helps if you go looking; Haqdarshak helps if an agent reaches you; Yojana Saathi keeps watching for your whole family, for free, and tells you what to do next.

**Differentiators (priority order):** 1) proactive change detection and alerts, 2) household-level view, 3) document gap guidance, 4) near-miss explanations.

**Scope (MVP):** central schemes + Uttar Pradesh; ~100 schemes; user groups: students, farmers, senior citizens/widows; Hindi + English; 8 weeks; solo developer.

**Primary user:** the family's "digital helper" (e.g. a college student) who sets things up for parents and grandparents.

## 2. Features

**MVP:** household setup (members, attributes, documents held) · rules engine (eligible / near-miss / not eligible / unknown) · family dashboard · scheme detail page with ticked-off reasons · document gap checker + how-to-get guides · LLM rule extraction · admin review queue + scheme versioning · weekly change-detection crawler · alerts by **email** (deadline, new matching scheme, age threshold, rule change) · Hindi + English · login (Google or email OTP).

**v2:** SMS alerts · ask-a-question chat grounded in a scheme record · WhatsApp bot + voice · assisted mode for NGO/CSC volunteers · more states.

**Not building:** applying on the user's behalf · storing Aadhaar/bank/certificate numbers · LLM deciding eligibility.

## 3. Key screens

Home · household setup wizard · family dashboard · scheme detail · document guide · alerts & settings · admin review queue · admin scheme editor.

## 4. Architecture

Three layers:

- **Pipeline (weekly):** crawler (fetch, clean, hash; skip unchanged) → LLM extractor (text → rule JSON + source quote per rule) → validator (allowed fields, valid dates) → admin review (approve/edit/reject → new scheme version).
- **Core:** PostgreSQL (schemes, versions, households) · rules engine (pure function, no DB or network) · FastAPI backend · alert scheduler (daily: deadlines in 14 and 3 days, age thresholds, changed results).
- **Interfaces:** Next.js web app (family) · admin console · email alerts.

Only approved rules reach the database. Every eligibility answer, on screen or in an alert, comes from the same rules engine.

## 5. Data model (MVP)

| Table | Key fields |
| --- | --- |
| schemes | id, slug, name_en, name_hi, level (central/state), state, category, official_url, status (active/closed/paused/merged/renamed), current_version_id |
| scheme_versions | id, scheme_id, version_no, rules_json, benefit_text_en, benefit_text_hi, deadline_start, deadline_end, source_url, source_hash, verified_at, approved_by |
| documents | id, code, name_en, name_hi, how_to_get_en, how_to_get_hi, official_link |
| scheme_documents | scheme_version_id, document_code, required, applies_to |
| users | id, email, language, alert_channel |
| households | id, user_id, state, district, area_type, income_band, category |
| members | id, household_id, nickname, relation, birth_year, gender, marital_status, occupation, education, is_student, disability |
| member_documents | member_id, document_code, has |
| eligibility_results | member_id, scheme_version_id, status, failed_rules_json, computed_at |
| review_items / alerts | pipeline proposals / sent alerts with type and status |

## 6. Rule format

```json
{
  "all": [
    {"field": "state", "op": "eq", "value": "UP"},
    {"field": "gender", "op": "eq", "value": "female"},
    {"field": "marital_status", "op": "eq", "value": "widow"},
    {"field": "age", "op": "gte", "value": 18},
    {"field": "income_band_max", "op": "lte", "value": 200000},
    {"any": [
      {"field": "category", "op": "in", "value": ["SC", "ST", "OBC"]},
      {"field": "area_type", "op": "eq", "value": "rural"}
    ]}
  ],
  "fixable": ["has_bank_account", "farmer_registered"]
}
```

- Operators: eq, neq, in, not_in, gte, lte, between, is_true. Combinators: all, any, not.
- Fields only from a fixed allowed list (member + household attributes). Unknown field → manual review.
- Result: **eligible** (all pass) · **near_miss** (fails only fixable rules) · **not_eligible** · **unknown** (needed attribute missing → ask the user).
- Income is stored as a band; compare with the band's upper edge; borderline → unknown.

## 7. Data freshness

Sources in priority: scheme's official portal/guidelines → myScheme pages → UP department portals → press releases (manual in MVP). Respect terms of use and robots.txt; crawl slowly; cache. Pipeline: fetch → hash diff → extract → validate → human review → publish new version → recompute eligibility → alerts. Renamed/merged schemes point to successors; closed schemes are hidden but kept; 404 twice → review; "last verified" shown on every scheme; unverified for 60 days → flagged; users can report outdated info.

## 8. Tech stack

FastAPI (Python 3.12) · PostgreSQL on Neon/Supabase + SQLAlchemy 2.0 + Alembic · own rules engine module · LLM via one wrapper (Claude or Gemini) · APScheduler for jobs · httpx + BeautifulSoup + pdfplumber · Next.js + TypeScript + Tailwind + next-intl · Auth: Google + email OTP · Email: Resend or Brevo · pytest, ruff, Playwright · GitHub Actions CI · Vercel (frontend), Render (backend) · Sentry.

## 9. Repository structure

```
yojana-saathi/
├── CLAUDE.md
├── PROJECT_SPEC.md
├── README.md
├── .github/workflows/ci.yml
├── backend/
│   ├── app/
│   │   ├── main.py, config.py
│   │   ├── db/          # models, session, migrations
│   │   ├── api/         # auth, households, members, schemes, eligibility, admin
│   │   ├── rules/       # engine.py (owner writes), fields.py, explain.py
│   │   ├── pipeline/    # crawler, change_detect, extractor, validator
│   │   ├── alerts/      # scheduler, triggers, email
│   │   └── llm/         # client wrapper, prompts
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/  components/  messages/ (en.json, hi.json)
│   └── .env.example
├── data/
│   ├── schemes_seed/    # hand-labelled scheme JSON (ground truth)
│   ├── documents.json
│   └── test_profiles/   # family profiles with expected results
└── docs/
    ├── architecture.md
    ├── decisions/
    └── evaluation.md
```

## 10. Success metrics

Rule extraction accuracy vs 50 hand-labelled schemes (target 90%+ per condition) · eligibility accuracy on 40 test profiles in CI (100%) · change detection on simulated edits (all caught) · 30+ real families tested, average 2+ newly discovered schemes · setup under 5 minutes.

## 11. Phases

1. **Week 1 — Validate and set up:** interviews, repo, CI, hello-world deploy; hand-label 30 schemes. *Gate:* 30 labelled, app deployed.
2. **Weeks 2–3 — Core engine:** rules engine + near-miss, test profiles in CI; LLM extractor + validator with accuracy script. *Gate:* tests pass, accuracy measured.
3. **Weeks 4–6 — Product:** APIs, auth, wizard, dashboard, scheme pages, document guides, Hindi, ~100 schemes. *Gate:* a real family completes setup on the live site.
4. **Week 7 — Freshness and alerts:** crawler, change detection, review queue, versioning, email alerts. *Gate:* a simulated page change flows through to an alert.
5. **Week 8 — Launch and measure:** test with families, metrics, README with demo GIF.
