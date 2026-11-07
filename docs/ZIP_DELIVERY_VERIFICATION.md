# PranaGuard v6 ZIP delivery verification

Deliverable: `PranaGuard-v6-Complete-Enhanced-Platform.zip` (entire runnable project; no GitHub access was available, so no PR was raised — stated honestly).

## Archive contents (final)

- All source (backend, frontend, scripts), frozen ML artifacts, datasets (120 synthetic patients / 3,000 states, SHA-digest-guarded), migrations `001–005`, docs (README, implementation/caveat/fairness/study reports, verification evidence incl. `docs/v6-verification/`), tests (`backend/tests/`, `frontend/src/**`). Built `frontend/dist/` is NOT included; run `npm run build`.
- Excluded: `.git/`, `.venv/`, `node_modules/`, caches (`__pycache__`, `.pytest_cache`, …), dev scratch (`data/tmp/`), any secrets (none exist).

## Integrity

- File count and byte size of the archive as delivered: **381 files, 13915215 bytes, DEFLATE-compressed**
- SHA-256 of the archive content **excluding this document** (deterministic rezip comparable): **9b21b2c1ca10a1c5d4833e9260d09b2586abb7f433c9c704098d9b45050df4f9**
- SHA-256 of the delivered ZIP file itself is shipped alongside it in `PranaGuard-v6-Complete-Enhanced-Platform.sha256` (authoritative integrity digest).

Self-reference note: a hash recorded inside a file can never cover its own container, so the archive-internal
hash covers all bytes except this document, and the authoritative full-archive digest lives in the sidecar
file next to the ZIP.

## Clean-extraction verification performed

Full steps and results: see `docs/v6-verification/V6_ACCEPTANCE.md`.
