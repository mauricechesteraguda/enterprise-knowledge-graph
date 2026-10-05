# type-10052026-Maurice: Publish bounded operational performance contracts.
"""Fixed service budgets used by API and dashboard operations."""
from __future__ import annotations

from dataclasses import dataclass

from kg.observability.tracing import trace_call


@dataclass(frozen=True)
class Budgets:
    # type-10052026-Maurice: Keep limits aligned with API safety caps.
    health_p95_ms: int
    query_p95_ms: int
    ask_p95_ms: int
    etl_seconds: int
    context_tokens: int
    evidence_rows: int


@trace_call
def configured() -> Budgets:
    # type-10052026-Maurice: Return deterministic upper bounds, not live customer measurements.
    return Budgets(250, 1000, 2000, 60, 8000, 50)
