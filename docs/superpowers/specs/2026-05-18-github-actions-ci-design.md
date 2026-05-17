# GitHub Actions CI Pipeline — Design Spec

**Date:** 2026-05-18
**Project:** verbal-fluency-iq

---

## Overview

Add a GitHub Actions CI pipeline that runs lint, type-checking, and tests in parallel on every push and pull request. Three independent jobs run concurrently so failures in any dimension are visible at once.

---

## Triggers

- `push` to any branch
- `pull_request` targeting `main`

---

## Jobs

### `lint`

- Runner: `ubuntu-latest`
- Tool: `ruff` (check + format --check)
- Installs: ruff only (from `requirements-dev.txt`)
- Cache: pip cache keyed on `requirements-dev.txt` hash
- Fast — no ML deps, expected runtime < 30 s

### `typecheck`

- Runner: `ubuntu-latest`
- Tool: `mypy mcp-server/`
- Installs: mypy + type stubs (from `requirements-dev.txt`)
- Cache: pip cache keyed on `requirements-dev.txt` hash
- Expected runtime < 60 s

### `test`

- Runner: `ubuntu-latest`
- Tool: `pytest tests/`
- Installs: full `requirements.txt` (spaCy, sentence-transformers, etc.)
- Cache:
  - pip cache keyed on `requirements.txt` hash
  - spaCy model cache at `~/.cache/` keyed on spaCy version
- Post-install: `python -m spacy download en_core_web_sm`
- Expected first-run: 4–6 min (sentence-transformers download); cached: ~90 s

---

## File Layout

```
.github/
  workflows/
    ci.yml          ← single workflow file with 3 parallel jobs
requirements-dev.txt  ← ruff, mypy, mypy stubs (new file)
```

`requirements.txt` is unchanged — dev tools stay out of production deps.

---

## Caching Strategy

Two cache keys:

| Cache | Key | Path |
|---|---|---|
| pip (prod) | `requirements.txt` SHA | `~/.cache/pip` |
| pip (dev) | `requirements-dev.txt` SHA | `~/.cache/pip` |
| spaCy model | spaCy version string | `~/.cache/` |

sentence-transformers caches its model at `~/.cache/huggingface/` automatically via the pip cache restore — no explicit cache step needed since the model files live inside the pip cache directory on GitHub runners.

---

## Error Handling

- Each job fails independently — a lint failure does not cancel the test job.
- `continue-on-error: false` (default) so PR checks block on any failure.

---

## Out of Scope

- PyPI publish
- Docker build
- Multi-OS matrix
- Coverage reporting (can be added later)
