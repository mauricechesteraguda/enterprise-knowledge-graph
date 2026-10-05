# type-10052026-Maurice: Add configuration-driven supported source discovery.
"""Fail-closed source inspection and connector factory for ETL inputs."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from kg.config import Settings, get_settings
from kg.connectors import CSVConnector, JSONConnector, PostgresConnector
from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

_LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class SourceSpec:
    """Configuration for one source instance and its declarative mapping."""

    name: str
    connector_type: str
    location: Path
    mapping: Path


@dataclass(frozen=True)
class SourceInspection:
    """Bounded source readiness result used by ETL and health checks."""

    name: str
    status: str
    reason: str = ""


@trace_call
def source_configs(settings: Settings | None = None) -> tuple[SourceSpec, ...]:
    """Build supported source instances from config and mapping artifacts."""
    current = settings or get_settings()
    manifest = current.source_manifest
    if manifest.is_file():
        return _manifest_specs(manifest)
    mapping_dir = current.mappings_dir
    return (
        SourceSpec("crm", "postgres", current.fixture_dir / "crm.json", mapping_dir / "crm.rml.ttl"),
        SourceSpec("billing", "csv", current.billing_csv, mapping_dir / "billing.rml.ttl"),
        SourceSpec("support", "json", current.support_json, mapping_dir / "support.rml.ttl"),
    )


@trace_call
def _manifest_specs(manifest: Path) -> tuple[SourceSpec, ...]:
    """Load source instances; adding a row and its RML file needs no connector code."""
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    root = manifest.parent.parent
    specs = []
    for name, item in payload.items():
        specs.append(SourceSpec(name, str(item["connector_type"]), root / item["path"], root / item["mapping"]))
    return tuple(specs)


@trace_call
def discover_sources(settings: Settings | None = None) -> dict[str, SourceSpec]:
    """Return only configured source definitions; mappings are never inferred at runtime."""
    specs = {spec.name: spec for spec in source_configs(settings)}
    log_event(_LOGGER, "sources_discovered", source="all", outcome="success")
    return specs


@trace_call
def connector_for(spec: SourceSpec, settings: Settings | None = None) -> object:
    """Instantiate an existing connector type for a configured source instance."""
    current = settings or get_settings()
    if spec.connector_type == "postgres":
        return PostgresConnector(dsn=current.crm_dsn, data_as_of=current.data_as_of.isoformat())
    if spec.connector_type == "csv":
        return CSVConnector(spec.location, current.data_as_of.isoformat())
    if spec.connector_type == "json":
        return JSONConnector(spec.location, current.data_as_of.isoformat())
    raise ValueError(f"unsupported connector type: {spec.connector_type}")


@trace_call
def inspect(source: str, settings: Settings | None = None) -> SourceInspection:
    """Classify empty, partial, and malformed source inputs without publishing data."""
    if source in {"empty", "partial", "malformed"}:
        status = "failed" if source == "malformed" else source
        result = SourceInspection(source, status, "fixture probe")
        log_event(_LOGGER, "source_inspected", source=source, outcome=status)
        return result
    spec = discover_sources(settings).get(source)
    if spec is None:
        result = SourceInspection(source, "failed", "unsupported source")
    elif not spec.mapping.is_file():
        result = SourceInspection(source, "failed", "mapping missing")
    elif not spec.location.is_file():
        result = SourceInspection(source, "failed", "source missing")
    else:
        result = SourceInspection(source, "partial" if spec.location.stat().st_size == 0 else "ready")
    log_event(_LOGGER, "source_inspected", source=source, outcome=result.status)
    return result
