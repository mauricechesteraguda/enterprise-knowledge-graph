# knowledge-graph

## Foundation

This repository uses a pinned Python 3.11–3.13 package with reproducible `make` targets:
`make install`, `make check`, and `make test`. The foundation runs without cloud credentials.
Copy `.env.example` to `.env` for local settings; secrets must never be committed.

Ownership boundaries are explicit: `src/kg/ports.py` owns typed connector, graph-store, and
LLM seams; later tickets own concrete adapters and orchestration. `src/kg/api/` owns versioned
HTTP composition, while `src/kg/observability/` owns bounded JSON events, Prometheus output,
and external session tracing. Artifacts belong under the ignored `artifacts/` run directory.
