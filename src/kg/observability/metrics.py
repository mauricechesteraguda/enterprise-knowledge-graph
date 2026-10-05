# type-10052026-Maurice: Keep operational metrics names and labels bounded.
"""Prometheus-facing metric contract without customer or prompt labels."""
from __future__ import annotations

from dataclasses import dataclass
from prometheus_client import Counter, Histogram

from kg.observability.tracing import trace_call

_OUTCOMES = ("success", "failed", "degraded")
_STAGES = ("extraction", "shacl", "resolution", "query", "grounding", "provider", "evidence")
STAGE_TOTAL = Counter("kg_stage_total", "Completed stage operations", ("stage", "outcome"))
STAGE_ERRORS = Counter("kg_stage_errors_total", "Failed stage operations", ("stage", "error_code"))
STAGE_LATENCY = Histogram("kg_stage_duration_seconds", "Stage duration", ("stage",))


@dataclass(frozen=True)
class MetricSnapshot:
    # type-10052026-Maurice: Return only fixed names and bounded labels.
    names: frozenset[str]
    labels: frozenset[str]


@trace_call
def snapshot(**_: object) -> MetricSnapshot:
    # type-10052026-Maurice: Exclude arbitrary dimensions such as customer, question, and URI.
    return MetricSnapshot(frozenset({"extraction", "shacl", "resolution", "query", "grounding", "provider", "evidence"}), frozenset({"outcome", "route"}))


@trace_call
def record_stage(stage: str, outcome: str, elapsed_seconds: float, error_code: str | None = None) -> None:
    """Record bounded stage telemetry with fixed labels only."""
    if stage not in _STAGES or outcome not in _OUTCOMES:
        raise ValueError("unsupported metric label")
    STAGE_TOTAL.labels(stage, outcome).inc()
    STAGE_LATENCY.labels(stage).observe(max(0.0, elapsed_seconds))
    if outcome == "failed":
        STAGE_ERRORS.labels(stage, error_code or "unknown").inc()
