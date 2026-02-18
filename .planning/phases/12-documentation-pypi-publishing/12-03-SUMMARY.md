---
phase: 12-documentation-pypi-publishing
plan: 03
status: complete
started: 2026-02-17
completed: 2026-02-17
duration: ~5min
---

## What was built

Package build verification, GitHub Actions CI/CD workflows, and PyPI publishing.

### key-files

#### created
- `.github/workflows/docs.yml` — auto-deploys docs to GitHub Pages on push to main
- `.github/workflows/publish.yml` — publishes to PyPI on GitHub release via trusted publisher (OIDC)

#### modified
- `.github/workflows/publish.yml` — fixed artifact path (dist/ not sdk/dist/)

### Verification results
- `uv build --package kalshibook` produces valid wheel with py.typed
- Package installs and imports in clean venv
- mypy --strict passes on consumer code
- Published to PyPI as kalshibook v0.1.0
- Docs auto-deployed to GitHub Pages

### Deviations
1. **Artifact path fix (Rule 1):** publish.yml initially used `sdk/dist/` for upload-artifact but `uv build --package kalshibook` outputs to `dist/` at repo root. Fixed to `dist/`.

## Self-Check: PASSED
- [x] uv build --package kalshibook succeeds
- [x] py.typed present in wheel
- [x] Package installs in clean venv
- [x] mypy --strict passes on consumer code
- [x] GitHub Actions workflows created and functional
- [x] Published to PyPI via trusted publisher
