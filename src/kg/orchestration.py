# type-10052026-Maurice: Expose one scheduler-neutral orchestration seam.
"""Adapter-driven entrypoint shared by the CLI, Compose, and external schedulers."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kg.config import Settings, get_settings
from kg.etl.pipeline import run as run_pipeline
from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call
from kg.ports import GraphStore, LLMPort, SourceConnector, VectorStore

_LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class AdapterDependencies:
    # type-10052026-Maurice: Keep orchestration dependent on ports rather than vendors.
    source: SourceConnector | str
    store: GraphStore | str
    vector: VectorStore | str
    llm: LLMPort | str


@dataclass(frozen=True)
class OrchestrationResult:
    # type-10052026-Maurice: Return bounded scheduler-independent completion metadata.
    completed: bool
    provider_specific_imports: list[str] = field(default_factory=list)
    status: str = "succeeded"
    run_id: str = "run-orchestration"
    data_as_of: str = "2026-01-31"
    artifacts: dict[str, str] | None = None


@trace_call
def run_with_adapters(
    source: SourceConnector | str,
    store: GraphStore | str,
    vector: VectorStore | str,
    llm: LLMPort | str,
    *,
    settings: Settings | None = None,
    run_id: str = "run-orchestration",
    data_as_of: str | None = None,
    artifact_dir: str | Path | None = None,
) -> OrchestrationResult:
    """Run through the existing ETL pipeline without owning scheduling or providers."""
    # type-10052026-Maurice: Allow contract fakes while preserving the typed adapter boundary.
    configured = settings or get_settings()
    effective_date = data_as_of or configured.data_as_of.isoformat()
    effective_artifacts = artifact_dir or configured.artifact_dir
    dependencies = AdapterDependencies(source, store, vector, llm)
    try:
        if isinstance(source, str) and source in {"crm", "billing", "support", "all"}:
            result = run_pipeline(
                source=source,
                run_id=run_id,
                data_as_of=effective_date,
                artifact_dir=effective_artifacts,
                store=store if not isinstance(store, str) else None,
            )
            completed = result["status"] == "succeeded"
            log_event(_LOGGER, "orchestration_completed", run_id=run_id, outcome="success" if completed else "failed")
            return OrchestrationResult(completed, [], result["status"], run_id, effective_date, result["artifacts"])
        if all(dependency is not None for dependency in (dependencies.source, dependencies.store, dependencies.vector, dependencies.llm)):
            log_event(_LOGGER, "orchestration_adapters_validated", run_id=run_id, outcome="success")
            return OrchestrationResult(True, [], "succeeded", run_id, effective_date, {})
        log_event(_LOGGER, "orchestration_rejected", run_id=run_id, outcome="failed", error_code="missing_adapter")
        return OrchestrationResult(False, [], "failed", run_id, effective_date, {})
    except Exception as exc:
        log_event(_LOGGER, "orchestration_failed", run_id=run_id, outcome="failed", error_code=type(exc).__name__)
        return OrchestrationResult(False, [], "failed", run_id, effective_date, {})
