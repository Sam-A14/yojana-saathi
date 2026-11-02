# 007 — Gemini retries and the model setting

## Context
The first real extraction runs hit two avoidable problems. Gemini answers HTTP 429 (quota) and 503
(overloaded) for short periods, which failed a whole manual run. And a GitHub repository variable
that is unset reaches the job as an empty string, not as "missing", so a model name can be blank.
The first run on pm-kisan also dropped an exception ("Excluding Group D") from a pension exclusion.

## Decision
- `GeminiClient` retries up to 3 times, waiting 5s, 15s, 45s, on HTTP 429/503, timeouts and
  connection errors. After that it raises `LLMError` saying how many retries it made and why the
  last one failed. 400/403/404 fail at once: a wrong key, model name or request cannot be fixed by
  waiting. The wait function is injected so tests never really sleep.
- `Settings.llm_model` treats an empty or whitespace value as "use `DEFAULT_LLM_MODEL`"
  (`gemini-3.6-flash`). The workflow passes `vars.LLM_MODEL` straight through.
- The prompt says an exception in a rule's quote must be encoded on the same member, as
  `all[...]` inside `any_member`, and shows a worked example. The example is a Python value that a
  test validates with the rules engine, so it cannot drift into an invalid rule.

## Alternatives
- Fix the empty variable only in the workflow (export `LLM_MODEL` when non-empty): protects only
  that one place. The config validator also protects local `.env` files.
- Use a retry library: one more dependency to learn for a loop of ten lines.
- Retry every error: hides a wrong key or model name behind a minute of waiting.

## Consequences
- A call can now wait up to 65 seconds before failing. Fine for a manual job, wrong for a web
  request; the client is only used by the extraction job.
- A blank `LLM_MODEL` can no longer be used to detect a misconfigured environment.
- The prompt rule is tested only as text. Whether the real model obeys it is checked by re-running
  the pm-kisan extraction after merge.
