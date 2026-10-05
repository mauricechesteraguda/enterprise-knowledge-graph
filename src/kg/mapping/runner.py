# type-10052026-Maurice: Define the executable RML mapping seam and fail-closed results.
"""Small offline RML runner seam; external morph-kgc can replace the runtime."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence, cast

from kg.connectors import CSVConnector, JSONConnector, PostgresConnector
from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call
from kg.ports import SourceRecord

_LOGGER = get_logger(__name__)


class SourceExtractor(Protocol):
    def extract(self, run_id: str) -> Sequence[SourceRecord]: ...


@dataclass(frozen=True)
class MappingResult:
    source: str
    records: Sequence[SourceRecord]
    source_ids_preserved: bool
    mapping_path: Path


class MappingRunner:
    # type-10052026-Maurice: Execute one named mapping with no publication side effects.
    @trace_call
    def __init__(self, mapping_dir: str | Path = "mappings") -> None:
        self.mapping_dir = Path(mapping_dir)

    @trace_call
    def map_source(self, source: str, connector: SourceExtractor | None = None, run_id: str = "mapping-run") -> MappingResult:
        mapping_path = self.mapping_dir / f"{source}.rml.ttl"
        if not mapping_path.is_file():
            raise FileNotFoundError(f"mapping not found for source: {source}")
        if connector is None:
            raise ValueError("connector is required at the mapping seam")
        records = connector.extract(run_id)
        ids = [record.source_record_id for record in records]
        if not all(ids) or len(ids) != len(set(ids)):
            raise ValueError("source IDs must be present and unique")
        result = MappingResult(source, records, True, mapping_path)
        log_event(_LOGGER, "mapping_executed", source=source, run_id=run_id, outcome="success")
        return result


@trace_call
def map_source(source: str, run_id: str = "mapping-run", fixture_dir: str | Path = "data/raw", mapping_dir: str | Path = "mappings") -> MappingResult:
    """Public mapping invocation seam for supported committed sources."""
    root = Path(fixture_dir)
    connectors: dict[str, SourceExtractor] = {"crm": PostgresConnector(rows=_crm_rows(root / "crm.json")), "billing": CSVConnector(root / "billing.csv"), "support": JSONConnector(root / "support.json")}
    return MappingRunner(mapping_dir).map_source(source, connectors[source], run_id)


@trace_call
def _crm_rows(path: Path) -> list[dict[str, object]]:
    import json
    return cast(list[dict[str, object]], json.loads(path.read_text(encoding="utf-8")))
