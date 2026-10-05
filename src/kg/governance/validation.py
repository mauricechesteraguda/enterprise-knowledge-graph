# type-10052026-Maurice: Make validation fail closed and preserve machine-readable quarantine evidence.
"""SHACL validation gate with a deterministic fallback for minimal installations."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

_LOGGER = get_logger(__name__)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_STATUSES = {"Paid", "Unpaid", "Overdue"}
_PRIORITIES = {"Low", "Medium", "High"}
_SHAPES_PATH = Path(__file__).resolve().parents[3] / "shapes" / "shapes.ttl"


class Report(set[str]):
    """A set-like report that also exposes mapping-style fields for old contracts."""

    # type-10052026-Maurice: Preserve report fields while supporting legacy set-style assertions.
    @trace_call
    def __init__(self, values: dict[str, str]) -> None:
        super().__init__(values)
        self._values = values

    # type-10052026-Maurice: Expose machine-readable report keys without source payloads.
    @trace_call
    def keys(self):
        return self._values.keys()

    # type-10052026-Maurice: Permit stable field access for quarantine consumers.
    @trace_call
    def __getitem__(self, key: str) -> str:
        return self._values[key]


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of the publication gate; rejected records are never publishable."""

    published: bool
    report: dict[str, Any] = field(default_factory=dict)
    quarantined: tuple[dict[str, Any], ...] = ()


# type-10052026-Maurice: Normalize records without retaining unrestricted source content.
@trace_call
def _violations(record: dict[str, Any], run_id: str) -> list[dict[str, str]]:
    kind = str(record.get("type", ""))
    source = str(record.get("source_record_id", "unknown"))
    errors: list[tuple[str, str]] = []
    if kind == "Invoice":
        if record.get("status") not in _STATUSES:
            errors.append(("status", "Invoice status must be a known taxonomy value"))
        try:
            date.fromisoformat(str(record.get("due_date", "")))
        except ValueError:
            errors.append(("due_date", "Invoice due date must be an ISO date"))
    if kind == "SupportTicket":
        if not _EMAIL.fullmatch(str(record.get("email", ""))):
            errors.append(("ticket_email", "Ticket email must be valid"))
        if record.get("priority") not in _PRIORITIES:
            errors.append(("priority", "Ticket priority must be a known taxonomy value"))
    for field_name in ("source_system", "run_id", "data_as_of"):
        if not record.get(field_name):
            errors.append((field_name, f"{field_name} is required"))
    return [Report({"shape": f"{kind}Shape", "focus_node": source, "path": path, "message": message,
                    "source_record": source, "run_id": run_id}) for path, message in errors]


# type-10052026-Maurice: Persist only bounded report fields and fail closed on I/O errors.
@trace_call
def _persist(report: list[dict[str, Any]], report_path: str | Path | None) -> None:
    if report_path is None:
        return
    try:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([dict(item._values) if isinstance(item, Report) else item for item in report], sort_keys=True, indent=2), encoding="utf-8")
        log_event(_LOGGER, "validation_report_persisted", outcome="success")
    except Exception:
        log_event(_LOGGER, "validation_report_persistence_failed", outcome="failed", error_code="artifact_io")
        raise RuntimeError("validation report persistence failed") from None


# type-10052026-Maurice: Gate publication and quarantine all violations atomically.
@trace_call
def validate_and_quarantine(record: dict[str, Any], run_id: str, report_path: str | Path | None = None) -> ValidationResult:
    """Validate one source record; no invalid record can be marked published."""
    try:
        if not isinstance(record, dict) or not run_id:
            raise ValueError("record and run_id are required")
        violations = _violations(record, run_id)
        _persist(violations, report_path)
        result = ValidationResult(published=not violations, report=violations[0] if violations else {}, quarantined=tuple(violations))
        log_event(_LOGGER, "shacl_validation_completed", outcome="accepted" if result.published else "quarantined")
        return result
    except Exception:
        log_event(_LOGGER, "shacl_validation_failed_closed", outcome="failed", error_code="validation_runtime")
        raise


# type-10052026-Maurice: Exercise distinct malformed date, taxonomy, and email quarantine cases.
@trace_call
def validate_fixtures() -> list[dict[str, str]]:
    """Return deterministic reports for the documented invalid fixture classes."""
    fixtures = [
        {"type": "Invoice", "source_record_id": "billing-invalid-date", "status": "Paid", "due_date": "31-01-2026", "source_system": "billing", "data_as_of": "2026-01-31"},
        {"type": "Invoice", "source_record_id": "billing-invalid-status", "status": "Settled", "due_date": "2026-01-31", "source_system": "billing", "data_as_of": "2026-01-31"},
        {"type": "SupportTicket", "source_record_id": "support-invalid-email", "email": "not-an-email", "priority": "High", "source_system": "support", "data_as_of": "2026-01-31"},
    ]
    reports: list[dict[str, str]] = []
    for fixture in fixtures:
        reports.extend(_violations(fixture, "fixture-validation"))
    return reports


# type-10052026-Maurice: Run the real pySHACL gate when RDF dependencies are installed.
@trace_call
def validate_graph(data_graph: Any, run_id: str, report_path: str | Path | None = None) -> ValidationResult:
    """Validate an RDFLib graph with committed shapes, failing closed if unavailable."""
    try:
        from rdflib import Graph, Namespace
        from pyshacl import validate as pyshacl_validate

        shapes_graph = Graph().parse(_SHAPES_PATH, format="turtle")
        conforms, _, report_graph = pyshacl_validate(data_graph, shacl_graph=shapes_graph, inference="rdfs")
        sh = Namespace("http://www.w3.org/ns/shacl#")
        reports: list[Report] = []
        for result in report_graph.subjects(predicate=sh.resultSeverity):
            values = {
                "shape": str(report_graph.value(result, sh.sourceShape) or "unknown"),
                "focus_node": str(report_graph.value(result, sh.focusNode) or "unknown"),
                "path": str(report_graph.value(result, sh.resultPath) or "unknown"),
                "message": str(report_graph.value(result, sh.resultMessage) or "SHACL violation"),
                "source_record": str(report_graph.value(result, sh.focusNode) or "unknown"),
                "run_id": run_id,
            }
            reports.append(Report(values))
        _persist(reports, report_path)
        return ValidationResult(published=bool(conforms), report=reports[0] if reports else {}, quarantined=tuple(reports))
    except (ImportError, OSError, ValueError) as exc:
        log_event(_LOGGER, "shacl_runtime_unavailable", outcome="failed", error_code=type(exc).__name__)
        raise RuntimeError("RDF/SHACL validation unavailable; publication blocked") from None
