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
the same as `data/ground_truth/<slug>.json` if you have labelled that scheme by hand. With a
ground-truth file, the extraction run also reports precision and recall against it.

## Run it

Actions tab -> **Extract scheme rules** -> Run workflow (from `main`) -> type the slug. The proposal,
the validation result and the accuracy score appear in the run summary. The proposal is saved to
`review_items` with status `pending`; nothing is published until a person approves it.

## A second source in the same file

When the first source lacks something the scheme needs (PM-KISAN's PIB release of 2019 says who
qualifies but gives no amount), a second, official source can be added **below the first**, under
one label line that says what it is and why it was added, followed by its own URL line, then the
text word for word:

```
=== SECOND SOURCE, added for the benefit amount: <publisher>, "<title>", <date> ===
https://...
(The text below is copied word for word from that page.)

<the text>
```

Line 1 stays the first source's URL (it becomes the scheme's `source_url`). Quotes from either block
are accepted, because the extractor and the validator match against the whole file. Keep the label
and the second URL, so a reader can see which words came from where. When running **Add scheme**
with `bump_version` for such a scheme, paste the **whole file** as `source_text`: the run replaces
the file with what you paste.
