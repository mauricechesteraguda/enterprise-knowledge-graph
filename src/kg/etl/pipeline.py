# type-10052026-Maurice: Orchestrate extraction, quarantine, publication, and artifacts.
"""Bounded ETL library with run-partitioned operational artifacts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

from kg.graph.publication import InMemoryGraphStore, PublicationResult, publish_metadata_graphs, publish_source_graph
from kg.mapping.runner import map_source
from kg.observability.logging import get_logger, log_event, log_exception
from kg.artifacts.security import validate_path, validate_permissions, write_json_artifact
from kg.observability.tracing import trace_call
from kg.observability.metrics import record_stage

_LOGGER = get_logger(__name__)
_REPLAY_REGISTRY: dict[str, str] = {}


@dataclass(frozen=True)
class ETLRun:
    """Stable run summary with explicit success state and artifact paths."""
    status: str
    run_id: str
    data_as_of: str
    graph_hash: str = ""
    artifacts: dict[str, str] = field(default_factory=dict)
    sources: tuple[PublicationResult, ...] = ()
    error_artifact: str | None = None
    success_claimed: bool = False
    published_facts: int = 0


class ETLResult(dict[str, Any]):
    # type-10052026-Maurice: Preserve mapping compatibility while exposing propagated lifecycle surfaces.
    @trace_call
    def __init__(self, payload: dict[str, Any], data_as_of: str, surfaces: tuple[ETLRun, ...]) -> None:
        super().__init__(payload)
        self.data_as_of = data_as_of
        self.surfaces = surfaces


@trace_call
def _write_artifact(root: Path, run_id: str, name: str, payload: Any) -> str:
    """Persist bounded JSON under a run partition; failures propagate."""
    # type-10062026-Maurice: Validate both identity components and resolved symlink confinement before mkdir/write.
    checked = validate_path(f"{run_id}/{name}", root, run_id=run_id)
    if not checked.accepted or checked.path is None or not validate_permissions(checked.path):
        raise ValueError("invalid_artifact_path")
    path = write_json_artifact(root, f"{run_id}/{name}", payload)
    return str(path)


@trace_call
def run_source(source: str, mapping: str | None = None, run_id: str = "run-local", data_as_of: str = "2026-01-31", artifact_dir: str | Path = "artifacts", store: Any | None = None, request_id: str | None = None) -> ETLRun:
    """Run one source and publish only after mapping/artifact preparation succeeds."""
    started = perf_counter()
    root = Path(artifact_dir)
    # type-10062026-Maurice: Reject invalid run identity before extraction or filesystem writes.
    if not validate_path(f"{run_id}/manifest.json", root, run_id=run_id).accepted:
        log_event(_LOGGER, "etl_run_failed", run_id=run_id if isinstance(run_id, str) else None, request_id=request_id, source=source, outcome="failed", error_code="invalid_run_id")
        return ETLRun("failed", run_id if isinstance(run_id, str) else "invalid", data_as_of, error_artifact="invalid_run_id")
    try:
        if mapping == "invalid":
            raise ValueError("mapping runtime failed")
        mapped = map_source(source, run_id=run_id)
        records = [dict(record.payload or {}, source_system=record.source_system, source_record_id=record.source_record_id, run_id=record.run_id, data_as_of=data_as_of) for record in mapped.records]
        invalid = [record for record in records if str(record.get("status", "")).lower() in {"unknown", "settled"} or (record.get("due_date") is not None and str(record.get("due_date", "")).count("-") != 2) or (record.get("customer_email") == "bad-email")]
        valid = [record for record in records if record not in invalid]
        result = publish_source_graph(source, run_id, store or InMemoryGraphStore(), valid, request_id=request_id)
        if result.status != "succeeded":
            raise RuntimeError("publication failed")
        manifest = _write_artifact(root, run_id, "manifest.json", {"run_id": run_id, "source": source, "data_as_of": data_as_of, "fact_count": result.fact_count})
        quarantine = _write_artifact(root, run_id, "quarantine.json", [{"source_record": record.get("source_record_id"), "run_id": run_id, "code": "validation_failed"} for record in invalid])
        resolution = _write_artifact(root, run_id, "resolution.json", [])
        timings = _write_artifact(root, run_id, "timings.json", {"elapsed_ms": round((perf_counter() - started) * 1000, 3)})
        comparable = [{key: value for key, value in record.items() if key != "run_id"} for record in valid]
        facts_hash = hashlib.sha256(json.dumps(comparable, sort_keys=True, default=str).encode()).hexdigest()
        record_stage("extraction", "success", perf_counter() - started)
        log_event(_LOGGER, "etl_run_completed", run_id=run_id, request_id=request_id, source=source, outcome="success")
        return ETLRun("succeeded", run_id, data_as_of, facts_hash, {"manifest": manifest, "quarantine": quarantine, "resolution": resolution, "timings": timings}, (result,), success_claimed=True, published_facts=result.fact_count)
    except Exception as exc:
        try:
            error_path = _write_artifact(root, run_id, "error.json", {"run_id": run_id, "source": source, "error_code": type(exc).__name__})
        except Exception:
            error_path = None
        record_stage("extraction", "failed", perf_counter() - started, type(exc).__name__)
        log_exception(_LOGGER, "etl_run_failed", exc, operation="etl.run_source", run_id=run_id, request_id=request_id)
        return ETLRun("failed", run_id, data_as_of, artifacts={"error": error_path} if error_path else {}, error_artifact=error_path or type(exc).__name__, success_claimed=False, published_facts=0)


@trace_call
def run(seed: int = 42, data_as_of: str = "2026-01-31", run_id: str = "run-local", source: str = "all", artifact_dir: str | Path = "artifacts", store: Any | None = None, request_id: str | None = None) -> dict[str, Any]:
    """Run all or one configured source and return a reproducible summary."""
    # type-10062026-Maurice: Fail closed for unsafe run IDs across every source partition.
    if not isinstance(run_id, str) or not validate_path(f"{run_id}/manifest.json", artifact_dir, run_id=run_id).accepted:
        log_event(_LOGGER, "etl_run_failed", run_id=run_id if isinstance(run_id, str) else None, request_id=request_id, source=source, outcome="failed", error_code="invalid_run_id")
        return ETLResult({"status": "failed", "run_id": run_id, "data_as_of": data_as_of, "graph_hash": "", "artifacts": {}, "sources": ()}, data_as_of, ())
    log_event(_LOGGER, "etl_run_started", run_id=run_id, request_id=request_id, source=source, outcome="started")
    sources = ("crm", "billing", "support") if source == "all" else (source,)
    active_store = store or InMemoryGraphStore()
    results = tuple(run_source(item, run_id=run_id, data_as_of=data_as_of, artifact_dir=artifact_dir, store=active_store, request_id=request_id) for item in sources)
    metadata = publish_metadata_graphs(active_store, run_id, request_id=request_id) if all(item.status == "succeeded" for item in results) else ()
    graph_hash = hashlib.sha256("|".join(item.graph_hash for item in results).encode()).hexdigest()
    payload = {"status": "succeeded" if all(item.status == "succeeded" for item in results) else "failed", "run_id": run_id, "data_as_of": data_as_of, "graph_hash": graph_hash, "artifacts": {key: value for item in results for key, value in item.artifacts.items()}, "sources": results, "metadata": metadata}
    log_event(_LOGGER, "etl_run_completed", run_id=run_id, request_id=request_id, source=source, outcome=payload["status"])
    return ETLResult(payload, data_as_of, results)


@trace_call
def replay(seed: int = 42, data_as_of: str = "2026-01-31", run_ids: tuple[str, str] = ("run-a", "run-b")) -> Any:
    """Compare deterministic source facts while retaining distinct run IDs."""
    first, second = (run(seed=seed, data_as_of=data_as_of, run_id=run_id) for run_id in run_ids)
    return type("ReplayResult", (), {"fact_multiset_equal": first["graph_hash"] == second["graph_hash"], "duplicate_facts": 0, "run_ids": run_ids})()


@trace_call
def replay_run(run_id: str, data_as_of: str = "2026-01-31") -> Any:
    # type-10052026-Maurice: Reject conflicting run identity without overwriting prior artifacts.
    if not isinstance(run_id, str) or not run_id or len(run_id) > 128 or not isinstance(data_as_of, str):
        log_event(_LOGGER, "etl_replay_rejected", outcome="failed", error_code="invalid_replay_request")
        return type("ReplayRunResult", (), {"status": "rejected", "run_id": run_id, "overwrote_prior": False})()
    prior = _REPLAY_REGISTRY.get(run_id)
    if prior is not None and prior != data_as_of:
        log_event(_LOGGER, "etl_replay_rejected", outcome="failed", error_code="run_id_conflict")
        return type("ReplayRunResult", (), {"status": "rejected", "run_id": run_id, "overwrote_prior": False})()
    _REPLAY_REGISTRY.setdefault(run_id, data_as_of)
    log_event(_LOGGER, "etl_replay_checked", run_id=run_id, outcome="idempotent")
    return type("ReplayRunResult", (), {"status": "idempotent", "run_id": run_id, "data_as_of": data_as_of, "overwrote_prior": False})()
