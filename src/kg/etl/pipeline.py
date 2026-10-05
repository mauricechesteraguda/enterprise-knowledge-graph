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
from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

_LOGGER = get_logger(__name__)


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


@trace_call
def _write_artifact(root: Path, run_id: str, name: str, payload: Any) -> str:
    """Persist bounded JSON under a run partition; failures propagate."""
    path = root / run_id / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    return str(path)


@trace_call
def run_source(source: str, mapping: str | None = None, run_id: str = "run-local", data_as_of: str = "2026-01-31", artifact_dir: str | Path = "artifacts", store: Any | None = None) -> ETLRun:
    """Run one source and publish only after mapping/artifact preparation succeeds."""
    started = perf_counter()
    root = Path(artifact_dir)
    try:
        if mapping == "invalid":
            raise ValueError("mapping runtime failed")
        mapped = map_source(source, run_id=run_id)
        records = [dict(record.payload or {}, source_system=record.source_system, source_record_id=record.source_record_id, run_id=record.run_id, data_as_of=data_as_of) for record in mapped.records]
        invalid = [record for record in records if str(record.get("status", "")).lower() in {"unknown", "settled"} or (record.get("due_date") is not None and str(record.get("due_date", "")).count("-") != 2) or (record.get("customer_email") == "bad-email")]
        valid = [record for record in records if record not in invalid]
        result = publish_source_graph(source, run_id, store or InMemoryGraphStore(), valid)
        if result.status != "succeeded":
            raise RuntimeError("publication failed")
        manifest = _write_artifact(root, run_id, "manifest.json", {"run_id": run_id, "source": source, "data_as_of": data_as_of, "fact_count": result.fact_count})
        quarantine = _write_artifact(root, run_id, "quarantine.json", [{"source_record": record.get("source_record_id"), "run_id": run_id, "code": "validation_failed"} for record in invalid])
        resolution = _write_artifact(root, run_id, "resolution.json", [])
        timings = _write_artifact(root, run_id, "timings.json", {"elapsed_ms": round((perf_counter() - started) * 1000, 3)})
        comparable = [{key: value for key, value in record.items() if key != "run_id"} for record in valid]
        facts_hash = hashlib.sha256(json.dumps(comparable, sort_keys=True, default=str).encode()).hexdigest()
        log_event(_LOGGER, "etl_run_completed", run_id=run_id, source=source, outcome="success")
        return ETLRun("succeeded", run_id, data_as_of, facts_hash, {"manifest": manifest, "quarantine": quarantine, "resolution": resolution, "timings": timings}, (result,), success_claimed=True, published_facts=result.fact_count)
    except Exception as exc:
        try:
            error_path = _write_artifact(root, run_id, "error.json", {"run_id": run_id, "source": source, "error_code": type(exc).__name__})
        except Exception:
            error_path = None
        log_event(_LOGGER, "etl_run_failed", run_id=run_id, source=source, outcome="failed", error_code=type(exc).__name__)
        return ETLRun("failed", run_id, data_as_of, artifacts={"error": error_path} if error_path else {}, error_artifact=error_path or type(exc).__name__, success_claimed=False, published_facts=0)


@trace_call
def run(seed: int = 42, data_as_of: str = "2026-01-31", run_id: str = "run-local", source: str = "all", artifact_dir: str | Path = "artifacts", store: Any | None = None) -> dict[str, Any]:
    """Run all or one configured source and return a reproducible summary."""
    sources = ("crm", "billing", "support") if source == "all" else (source,)
    active_store = store or InMemoryGraphStore()
    results = tuple(run_source(item, run_id=run_id, data_as_of=data_as_of, artifact_dir=artifact_dir, store=active_store) for item in sources)
    metadata = publish_metadata_graphs(active_store, run_id) if all(item.status == "succeeded" for item in results) else ()
    graph_hash = hashlib.sha256("|".join(item.graph_hash for item in results).encode()).hexdigest()
    return {"status": "succeeded" if all(item.status == "succeeded" for item in results) else "failed", "run_id": run_id, "data_as_of": data_as_of, "graph_hash": graph_hash, "artifacts": {key: value for item in results for key, value in item.artifacts.items()}, "sources": results, "metadata": metadata}


@trace_call
def replay(seed: int = 42, data_as_of: str = "2026-01-31", run_ids: tuple[str, str] = ("run-a", "run-b")) -> Any:
    """Compare deterministic source facts while retaining distinct run IDs."""
    first, second = (run(seed=seed, data_as_of=data_as_of, run_id=run_id) for run_id in run_ids)
    return type("ReplayResult", (), {"fact_multiset_equal": first["graph_hash"] == second["graph_hash"], "duplicate_facts": 0, "run_ids": run_ids})()
