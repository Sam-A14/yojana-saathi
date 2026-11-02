# scheme_sources/

Scheme text pasted by hand, one file per scheme: `<slug>.txt`. The LLM extraction reads these
(`backend/app/pipeline/`); nothing here is loaded into the database.

## File format

- **Line 1:** the URL the text came from (`https://...`), nothing else on the line.
- **The rest:** the scheme text, copied from the official page or guidelines. Paste it as it is:
  the extractor checks that every source quote appears **word for word** in this text, so do not
  retype, translate or tidy it.

```
https://example.gov.in/some-scheme
Eligibility
Every woman aged 18 years or above whose family income is below ...
```

The file name must be the scheme's slug (lowercase words joined by `-`, for example `pm-kisan`),
the same as `data/schemes_seed/<slug>.json` if you have labelled that scheme by hand. With a seed
file, the extraction run also reports precision and recall against it.

## Run it

Actions tab -> **Extract scheme rules** -> Run workflow (from `main`) -> type the slug. The proposal,
the validation result and the accuracy score appear in the run summary. The proposal is saved to
`review_items` with status `pending`; nothing is published until a person approves it.
