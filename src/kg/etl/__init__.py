# type-10052026-Maurice: Keep ETL source discovery importable without eager services.
"""ETL orchestration and source discovery entry points."""

from typing import Any

from kg.etl.sources import SourceInspection, SourceSpec, connector_for, discover_sources, inspect, source_configs
from kg.observability.tracing import trace_call

__all__ = ["ETLRun", "run", "run_source", "replay", "SourceInspection", "SourceSpec", "connector_for", "discover_sources", "inspect", "source_configs"]


@trace_call
def __getattr__(name: str) -> Any:
    # type-10052026-Maurice: Preserve legacy ETL exports while keeping source probes lightweight.
    from kg.etl import pipeline
    if name in {"ETLRun", "run", "run_source", "replay"}:
        return getattr(pipeline, name)
    raise AttributeError(name)
