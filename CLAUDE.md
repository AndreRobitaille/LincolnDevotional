# Lincoln Daily Devotional

## Deploying

**Pushing to `main` deploys straight to production.** `.github/workflows/deploy.yml`
FTPS-uploads the repo root to the live cPanel host on every push to `main`. There is no
staging step and no manual gate. Work on a branch; merge only when the change is ready to
be live.

## Local dev server

```bash
python3 -m http.server 3000 --bind 0.0.0.0
```

Port 3000, bound to `0.0.0.0` so the site is reachable from other devices on the LAN for
mobile QA. (`AGENTS.md` still documents port 8000 / localhost — this supersedes it.)

## Tests

Run from the project root — the tests import `tools.*`, and `tests/` has no `__init__.py`,
so it only resolves with the repo root as cwd:

```bash
python3 -m unittest tests.test_generate_entry_pages tests.test_tag_entries_openai
```

They mock their network calls, so no API keys are needed. Coverage is limited to
`generate_entry_pages` and `tag_entries_openai`; nothing else in `tools/` has tests, and
the front-end has none at all. For UI changes, verify by hand: load a date, use the date
picker, toggle light/dark, and check the console for errors.

## API keys

Two scripts need secrets from `.env`:

- `tools/fetch_esv.py` → `ESV_API_KEY` (present)
- `tools/tag_entries_openai.py` → `OPENAI_API_KEY` (**not** in `.env`; supply it before running)

## Data files

The generated caches under `data/` are committed on purpose — `esv_cache.json` and
`entry_topics_cache.json` are checked in alongside the hand-maintained `entries.json`.
Regenerating them produces real diffs that belong in the commit; don't gitignore them or
discard the churn.

## Indentation

Mixed across the front-end, by file rather than by convention: `script.js` and
`permalink.js` use 4 spaces; `theme.js`, `explore.js`, and `static-entry-nav.js` use 2.
Match the file you're editing. Python in `tools/` is 4-space PEP 8 throughout.
