# type-10052026-Maurice: Implement swappable Postgres, CSV, and JSON source adapters.
"""Source connector adapters with uniform provenance-preserving records."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from kg.fixtures import raw_hash
from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call
from kg.ports import SourceRecord, validate_connector_record

_LOGGER = get_logger(__name__)


@trace_call
def _records(source: str, rows: Iterable[dict[str, Any]], run_id: str, data_as_of: str) -> list[SourceRecord]:
    """Attach stable IDs, hashes, source, run, and as-of metadata to rows."""
    result = []
    for row in rows:
        source_id = str(row.get("source_id", ""))
        record = SourceRecord(source, source_id, run_id, raw_hash(row), data_as_of, source, dict(row))
        result.append(validate_connector_record(record))
    log_event(_LOGGER, "source_extracted", source=source, run_id=run_id, outcome="success")
    return result


class CSVConnector:
    # type-10052026-Maurice: Read delimited fixtures without changing source values.
    @trace_call
    def __init__(self, path: str | Path, data_as_of: str = "2026-01-31") -> None:
        self.path, self.data_as_of = Path(path), data_as_of

    @trace_call
    def extract(self, run_id: str) -> Sequence[SourceRecord]:
        with self.path.open(newline="", encoding="utf-8") as stream:
            return _records("billing", csv.DictReader(stream), run_id, self.data_as_of)


class JSONConnector:
    # type-10052026-Maurice: Read JSON fixture arrays through the common connector port.
    @trace_call
    def __init__(self, path: str | Path, data_as_of: str = "2026-01-31") -> None:
        self.path, self.data_as_of = Path(path), data_as_of

    @trace_call
    def extract(self, run_id: str) -> Sequence[SourceRecord]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("support JSON must contain an array")
        return _records("support", payload, run_id, self.data_as_of)


class PostgresConnector:
    # type-10052026-Maurice: Accept injected rows for offline tests and real DB adapters.
    @trace_call
    def __init__(self, dsn: str = "", rows: Iterable[dict[str, Any]] | None = None, data_as_of: str = "2026-01-31") -> None:
        self.dsn, self.rows, self.data_as_of = dsn, rows, data_as_of

    @trace_call
    def extract(self, run_id: str) -> Sequence[SourceRecord]:
        if self.rows is None:
            raise RuntimeError("PostgresConnector requires an injected rows adapter in offline mode")
        return _records("crm", self.rows, run_id, self.data_as_of)
