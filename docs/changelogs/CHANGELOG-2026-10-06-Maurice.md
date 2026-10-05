# Changelog — 2026-10-06

## Enterprise KG MVP verification

- Fixed CI package completeness by anchoring runtime artifact ignores and tracking the artifact-security package.
- Added bounded request/run correlation across API, ETL, graph publication, and query boundaries.
- Hardened structured logging with allowlisted fields, bounded values, secret/PII redaction, and safe exception diagnostics.
- Hardened artifact-path confinement and typed adapter compatibility without exposing source payloads.

## Verification

- Full test suite: 67 passed; branch coverage 85.00%, meeting the configured 85% threshold.
- Documentation contract tests: 2 passed (`tc_032` and `tc_033`).
- CSV requirement mapping: 50 rows covering 33 requirements.
- Markdown local-link check: passed for `docs/**/*.md`.
- Compose configuration: `docker compose config` passed.
- `git diff --check`: passed.

## Verification commands

- `docker compose config`
- `docker compose --profile test run --rm tests`
- `docker compose --profile etl run --rm etl` (run twice for replay stability)

## Notes

- The local-link check covers relative Markdown links under `docs/`; it does not validate external URLs.
- Docker service execution and HTTP acceptance probes are recorded in `docs/results.md`.

Author Name: Aguda, Maurice
