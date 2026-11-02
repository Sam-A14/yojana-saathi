# data/

Hand-made data files. The database is loaded from these files, so a mistake here reaches families.

| Path | What it is |
| --- | --- |
| `documents.json` | The catalogue of documents (code, English and Hindi name). Checked by `documents.schema.json`. |
| `scheme.schema.json` | The rules for one scheme file. Checked by tests and by the seed loader. |
| `schemes_seed/*.json` | One file per scheme, labelled by hand. |
| `schemes_seed/TEMPLATE.json` | Copy this to start a new scheme. Never loaded. |
| `test_profiles/` | Planned: sample families with the expected result for each. |

## Label a new scheme

1. Copy `schemes_seed/TEMPLATE.json` to `schemes_seed/<slug>.json`. The file name **must equal** the
   `slug` inside (lowercase words joined by `-`, for example `pm-kisan`).
2. Fill it in from the scheme's **official** page. Put that page in `source_url`.
3. Keep `"$schema": "../scheme.schema.json"` at the top. VS Code then underlines mistakes as you type.
4. Leave `verified_at` as `null` until you (a person) have checked every rule against the official
   source, then set it to that day's date, for example `"2026-11-02"`.
5. In `labeller_notes`, say whether you reached the official page, and list official conditions the
   rule fields cannot express in `not_encoded`. Nothing in `labeller_notes` goes to the database.
6. Check it: `cd backend && pytest tests/test_seed_files.py`. Then open a pull request.

## Rule format

```json
{"all": [
  {"field": "age", "op": "gte", "value": 40},
  {"any": [{"field": "category", "op": "in", "value": ["SC", "ST"]},
           {"field": "area_type", "op": "eq", "value": "rural"}]},
  {"field": "has_land_record", "op": "is_true"}
 ],
 "fixable": ["has_land_record"]}
```

- Operators: `eq`, `neq`, `in`, `not_in`, `gte`, `lte`, `between` (two numbers), `is_true` (no value).
- Groups: `all`, `any`, `not`. The top level is always `{"all": [...]}`.
- `fixable`: fields whose failure the family can fix (usually a missing document). A person who
  fails only these is a "near miss".
- `field` must come from a fixed list in `scheme.schema.json`: the member and household attributes
  (`age`, `gender`, `marital_status`, `occupation`, `education`, `is_student`, `disability`,
  `state`, `district`, `area_type`, `income_band_max`, `category`) and one `has_<code>` field per
  document in `documents.json`. A typo fails the check instead of silently meaning "unknown".
- **Keep this list in sync with `backend/app/rules/fields.py`** when that file is added. A test
  already checks the `has_` fields against `documents.json`: adding a document means adding its
  `has_<code>` field to the schema in the same change.

## What happens when the loader runs

- Documents are matched by `code`, schemes by `slug`. Different text is updated in place.
- If a scheme's **rules, benefit text, deadlines, source or document list** change, a **new version**
  is added and made current. Old versions are kept, because eligibility results point at them.
- If only `verified_at` or `approved_by` changed, the current version is updated in place.
- A document removed from `documents.json` is not deleted from the database (something may still
  use it); the loader prints a warning.
- Any problem in any file means nothing is loaded.

## Example data

`pm-kisan.json` and `ignwps.json` are **examples, verify before use**. They were written from
memory because the official sites could not be reached in the session that wrote them, and each
says so in `labeller_notes`. They have `verified_at: null`. Do not treat them as correct until a
person has checked them against the official pages.
