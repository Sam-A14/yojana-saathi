# 011 — CORS for Vercel preview deployments

## Context
Every pull request gets a Vercel preview with its own URL, so `FRONTEND_URL` (one fixed origin)
cannot list them, and the preview site would be blocked by CORS when it calls the API.

## Decision
- Two optional settings, `VERCEL_PROJECT` and `VERCEL_TEAM` (the slugs in the preview URLs). When
  both are set, `config.vercel_preview_regex()` builds an anchored regex and `main.add_cors()` passes
  it to `allow_origin_regex`. `FRONTEND_URL` stays for production and is still checked first.
- The regex covers the two shapes Vercel uses: `https://<project>-<hash>-<team>.vercel.app` and
  `https://<project>-git-<branch>-<team>.vercel.app`. It starts with `^`, ends with `$`, requires
  https, and both slugs go through `re.escape`.
- Setting only one slug is a startup error (a half setting would silently allow nothing or too much).
- Production (Render) sets the two variables so previews can reach it; with them unset, only
  `FRONTEND_URL` is allowed.
- `add_cors()` is a small function so tests can build a throwaway app with chosen settings.

## Alternatives
- `allow_origins=["*"]`: no, and browsers refuse it for requests that carry an Authorization header anyway.
- A regex written by hand in one environment variable: easy to get wrong, hard to test; two plain
  slugs are harder to mistype and the code builds the pattern.
- Listing each preview URL: never keeps up.

## Consequences
- Anyone who can reach a preview URL can call the API from it. That is acceptable because the API
  holds no identity numbers and every household route still needs its own token. CORS only decides
  which sites a *browser* will let read the answers; it is not authentication.
- Residual risk: a Vercel team whose slug *ends with* our team slug could produce a URL matching
  the branch form (`...-git-<anything>-<our-team>`). Such a site would still not have any family's
  token, because tokens are in `localStorage` of our own origins, not sent by the browser automatically.
  If this ever matters, drop the branch form and keep only the per-deployment form.
- Vercel shortens very long branch names with a hash; those URLs still match the branch form.
