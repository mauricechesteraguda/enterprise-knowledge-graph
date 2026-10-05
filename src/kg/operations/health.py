# type-10052026-Maurice: Distinguish required dependency failure from degradation.
"""Dependency health summarization for readiness and operator surfaces."""
from __future__ import annotations

from dataclasses import dataclass

from kg.observability.tracing import trace_call


@dataclass(frozen=True)
class HealthSummary:
    # type-10052026-Maurice: Keep health state typed and free of dependency details.
    status: str
    required_failed: bool
    optional_failed: bool


@trace_call
def summarize(*, fuseki: str, crm: str, pgvector: str, provider: str) -> HealthSummary:
    # type-10052026-Maurice: Treat graph and CRM as required while vector/provider are optional.
    required_failed = fuseki != "ok" or crm != "ok"
    optional_failed = pgvector != "ok" or provider != "ok"
    state = "failed" if required_failed else ("degraded" if optional_failed else "ok")
    return HealthSummary(state, required_failed, optional_failed)
