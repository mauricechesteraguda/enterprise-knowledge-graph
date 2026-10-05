# type-10052026-Maurice: Implement the read-only bounded query catalog.
"""Allowlisted SPARQL 1.1 intents executed through a GraphStore seam."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF
from rdflib.query import ResultRow

from kg.observability.logging import get_logger, log_event
from kg.artifacts.security import write_json_artifact
from kg.ports import call_with_optional_context
from kg.observability.tracing import trace_call
from kg.observability.metrics import record_stage

_LOGGER = get_logger(__name__)
KG = Namespace("https://example.org/kg/")
_QUERY_DIR = Path(__file__).resolve().parents[3] / "queries"
_MAX_LIMIT = 1000
_MAX_TIMEOUT = 5
_SAFE_INTENT = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


@trace_call
def _query_file(name: str) -> Path:
    # type-10052026-Maurice: Resolve committed query assets from source and installed Compose layouts.
    candidates = (_QUERY_DIR / name, Path.cwd() / "queries" / name, Path("/app/queries") / name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"query asset unavailable: {name}")


@dataclass(frozen=True)
class CatalogIntent:
    # type-10052026-Maurice: Make catalog metadata stable and machine-readable.
    name: str
    query_file: str
    parameters: tuple[str, ...] = ()
    cap: int = _MAX_LIMIT
    timeout_seconds: int = _MAX_TIMEOUT
    expected_rows: int = 0
    elapsed_ms: float = 0.0


@dataclass(frozen=True)
class CatalogError:
    # type-10052026-Maurice: Keep rejection details bounded and non-sensitive.
    code: str
    message: str


@dataclass(frozen=True)
class CatalogResult:
    # type-10052026-Maurice: Return rows and execution metadata without raw query text.
    intent: str
    rows: tuple[dict[str, str], ...] = ()
    cap: int = _MAX_LIMIT
    timeout_seconds: int = _MAX_TIMEOUT
    elapsed_ms: float = 0.0
    truncated: bool = False
    mutated: bool = False
    store_calls: int = 0
    data_as_of: str = "2026-01-31"
    error: CatalogError | None = None


@dataclass(frozen=True)
class CatalogExecution:
    # type-10052026-Maurice: Describe an intent independently of execution output.
    name: str
    cap: int
    timeout_seconds: int
    elapsed_ms: float
    expected_rows: int
    result_count: int
    error: CatalogError | None = None


_INTENTS: dict[str, CatalogIntent] = {
    "cross_silo_unpaid_open_high": CatalogIntent(
        "cross_silo_unpaid_open_high", "cross_silo_unpaid_open_high.rq", expected_rows=1
    ),
    "canonical_identity_records": CatalogIntent(
        "canonical_identity_records", "canonical_identity_records.rq", expected_rows=1
    ),
    "unpaid_invoices_by_organization": CatalogIntent(
        "unpaid_invoices_by_organization", "unpaid_invoices_by_organization.rq", expected_rows=1
    ),
    "high_priority_products_quarter": CatalogIntent(
        "high_priority_products_quarter",
        "high_priority_products_quarter.rq",
        ("quarter_start", "quarter_end"),
        expected_rows=1,
    ),
    "person_account_invoice_product_ticket": CatalogIntent(
        "person_account_invoice_product_ticket",
        "person_account_invoice_product_ticket.rq",
        expected_rows=1,
    ),
    "orphan_tickets": CatalogIntent("orphan_tickets", "orphan_tickets.rq", expected_rows=1),
}
_ALIASES = {
    "unpaid_invoices": "unpaid_invoices_by_organization",
    "unpaid_open_high": "cross_silo_unpaid_open_high",
    "canonical_identities": "canonical_identity_records",
    "unpaid_by_organization": "unpaid_invoices_by_organization",
    "high_priority_products": "high_priority_products_quarter",
    "multihop_person_product": "person_account_invoice_product_ticket",
    "orphan_support_tickets": "orphan_tickets",
}


@trace_call
def _fixture_graph() -> Graph:
    # type-10052026-Maurice: Build the six-query offline fixture without customer data.
    graph = Graph()
    p = URIRef("https://example.org/kg/Person/p-001")
    account = URIRef("https://example.org/kg/Account/a-001")
    invoice = URIRef("https://example.org/kg/Invoice/i-001")
    line = URIRef("https://example.org/kg/InvoiceLine/il-001")
    product = URIRef("https://example.org/kg/Product/prod-001")
    ticket = URIRef("https://example.org/kg/SupportTicket/t-001")
    org = URIRef("https://example.org/kg/Organization/org-001")
    orphan = URIRef("https://example.org/kg/SupportTicket/t-orphan")
    graph.add((p, RDF.type, KG.Person))
    graph.add((p, KG.name, Literal("Fixture Person")))
    graph.add((p, KG.email, Literal("person@example.test")))
    graph.add((p, KG.sourceRecord, URIRef("https://example.org/kg/SourceRecord/crm/crm-001")))
    graph.add((p, KG.hasAccount, account))
    graph.add((p, KG.raisedTicket, ticket))
    graph.add((account, RDF.type, KG.Account))
    graph.add((account, KG.belongsToOrganization, org))
    graph.add((account, KG.hasInvoice, invoice))
    graph.add((invoice, RDF.type, KG.Invoice))
    graph.add((invoice, KG.status, KG.Unpaid))
    graph.add((invoice, KG.hasInvoiceLine, line))
    graph.add((line, RDF.type, KG.InvoiceLine))
    graph.add((line, KG.lineProduct, product))
    graph.add((product, RDF.type, KG.Product))
    graph.add((product, KG.name, Literal("Fixture Product")))
    graph.add((ticket, RDF.type, KG.SupportTicket))
    graph.add((ticket, KG.status, KG.Open))
    graph.add((ticket, KG.priority, KG.High))
    graph.add((ticket, KG.concernsProduct, product))
    graph.add((ticket, KG.openedAt, Literal("2026-01-15")))
    graph.add((orphan, RDF.type, KG.SupportTicket))
    graph.add((orphan, KG.status, KG.Open))
    graph.add((orphan, KG.priority, KG.Low))
    return graph


class RDFLibGraphStore:
    # type-10052026-Maurice: Provide a deterministic GraphStore implementation when Fuseki is absent.
    @trace_call
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph or _fixture_graph()
        self.calls = 0

    @trace_call
    def query(
        self, intent: str, parameters: dict[str, str], limit: int, timeout_seconds: int, *, request_id: str | None = None, run_id: str | None = None
    ) -> Sequence[dict[str, str]]:
        # type-10062026-Maurice: Accept bounded correlation while keeping query text and rows out of logs.
        self.calls += 1
        spec = _INTENTS.get(intent)
        if spec is None:
            raise ValueError("unknown intent")
        bindings: dict[str, Literal] = {}
        for key in spec.parameters:
            parts = key.split("_")
            binding_name = parts[0] + "".join(part.title() for part in parts[1:])
            bindings[binding_name] = Literal(parameters[key])
        rows = self.graph.query(
            _query_file(spec.query_file).read_text(encoding="utf-8"), initBindings=bindings
        )
        return [
            {str(variable): str(value) for variable, value in row.asdict().items()}
            for row in rows
            if isinstance(row, ResultRow)
        ][:limit]

    @trace_call
    def sparql(self, query: str, *, limit: int, timeout_seconds: int) -> Sequence[dict[str, str]]:
        # type-10052026-Maurice: Keep the local read-only SPARQL adapter bounded and injectable.
        self.calls += 1
        rows = self.graph.query(query)
        return [
            {str(variable): str(value) for variable, value in row.asdict().items()}
            for row in rows
            if isinstance(row, ResultRow)
        ][:limit]


@trace_call
def all_intents() -> tuple[CatalogIntent, ...]:
    # type-10052026-Maurice: Return the fixed catalog in deterministic order.
    return tuple(_INTENTS[name] for name in sorted(_INTENTS))


@trace_call
def _validate(
    intent: str, parameters: Mapping[str, str], limit: int, timeout_seconds: int
) -> tuple[str, CatalogIntent]:
    # type-10052026-Maurice: Fail closed before invoking any GraphStore method.
    if not isinstance(intent, str) or not _SAFE_INTENT.fullmatch(intent):
        raise ValueError("unsafe_intent")
    canonical = _ALIASES.get(intent, intent)
    spec = _INTENTS.get(canonical)
    if spec is None:
        raise ValueError("unknown_intent")
    if not isinstance(parameters, Mapping) or set(parameters) - set(spec.parameters):
        raise ValueError("invalid_parameters")
    if (
        limit < 1
        or limit > spec.cap
        or timeout_seconds < 1
        or timeout_seconds > spec.timeout_seconds
    ):
        raise ValueError("bounds_exceeded")
    for key in spec.parameters:
        value = parameters.get(key, "")
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError("invalid_parameter")
        date.fromisoformat(value)
    return canonical, spec


@trace_call
def _query_store(store: Any, intent: str, parameters: dict[str, str], limit: int, timeout_seconds: int, *, request_id: str | None = None, run_id: str | None = None) -> Sequence[dict[str, str]]:
    # type-10062026-Maurice: Forward optional correlation without requiring legacy fakes to change.
    return cast(Sequence[dict[str, str]], call_with_optional_context(store.query, intent, parameters, limit, timeout_seconds, request_id=request_id, run_id=run_id))


@trace_call
def execute(
    intent: str,
    parameters: Mapping[str, str],
    store: Any | None = None,
    limit: int = _MAX_LIMIT,
    timeout_seconds: int = _MAX_TIMEOUT,
    force_timeout: bool = False,
    request_id: str | None = None,
    run_id: str | None = None,
) -> CatalogResult:
    # type-10052026-Maurice: Run one allowlisted read-only intent with monotonic timing.
    started = time.monotonic()
    try:
        canonical, spec = _validate(intent, parameters, limit, timeout_seconds)
    except (TypeError, ValueError) as exc:
        code = (
            str(exc)
            if str(exc)
            in {
                "unsafe_intent",
                "unknown_intent",
                "invalid_parameters",
                "bounds_exceeded",
                "invalid_parameter",
            }
            else "invalid_parameter"
        )
        log_event(_LOGGER, "catalog_query_failed", intent=intent if isinstance(intent, str) else None, request_id=request_id, run_id=run_id, outcome="failed", error_code=code)
        return CatalogResult(
            intent,
            error=CatalogError(code, "query request rejected"),
            elapsed_ms=(time.monotonic() - started) * 1000,
        )
    if force_timeout:
        log_event(_LOGGER, "catalog_query_failed", intent=canonical, request_id=request_id, run_id=run_id, outcome="failed", error_code="query_timeout")
        return CatalogResult(
            canonical,
            cap=spec.cap,
            timeout_seconds=spec.timeout_seconds,
            elapsed_ms=timeout_seconds * 1000,
            error=CatalogError("query_timeout", "query exceeded timeout"),
        )
    graph_store = store or RDFLibGraphStore()
    try:
        rows = tuple(
            dict(row)
            for row in _query_store(graph_store, canonical, dict(parameters), min(limit, spec.cap), min(timeout_seconds, spec.timeout_seconds), request_id=request_id, run_id=run_id)
        )
        elapsed = (time.monotonic() - started) * 1000
        if elapsed > timeout_seconds * 1000:
            raise TimeoutError
        log_event(
            _LOGGER,
            "catalog_query",
            intent=canonical, request_id=request_id, run_id=run_id,
            elapsed_ms=round(elapsed, 3),
            outcome="success",
        )
        record_stage("query", "success", elapsed / 1000)
        return CatalogResult(
            canonical,
            rows,
            spec.cap,
            spec.timeout_seconds,
            elapsed,
            len(rows) >= limit,
            False,
            int(getattr(graph_store, "calls", 1)),
            error=None,
        )
    except TimeoutError:
        log_event(_LOGGER, "catalog_query_failed", intent=canonical, request_id=request_id, run_id=run_id, outcome="failed", error_code="query_timeout")
        record_stage("query", "failed", (time.monotonic() - started), "query_timeout")
        return CatalogResult(
            canonical,
            cap=spec.cap,
            timeout_seconds=spec.timeout_seconds,
            elapsed_ms=(time.monotonic() - started) * 1000,
            error=CatalogError("query_timeout", "query exceeded timeout"),
        )
    except Exception as exc:
        from kg.observability.logging import log_exception
        log_exception(_LOGGER, "catalog_query_failed", exc, operation="catalog.execute", request_id=request_id, run_id=run_id, error_code="query_failed")
        record_stage("query", "failed", (time.monotonic() - started), "query_failed")
        return CatalogResult(
            canonical,
            cap=spec.cap,
            timeout_seconds=spec.timeout_seconds,
            elapsed_ms=(time.monotonic() - started) * 1000,
            error=CatalogError("query_failed", "query execution failed"),
        )


@trace_call
def benchmark(store: Any | None = None) -> tuple[CatalogExecution, ...]:
    # type-10052026-Maurice: Emit stable benchmark records for all seeded intents.
    output: list[CatalogExecution] = []
    for spec in all_intents():
        params = {
            key: "2026-01-01" if key == "quarter_start" else "2026-04-01" for key in spec.parameters
        }
        result = execute(spec.name, params, store=store)
        output.append(
            CatalogExecution(
                spec.name,
                spec.cap,
                spec.timeout_seconds,
                result.elapsed_ms,
                spec.expected_rows,
                len(result.rows),
                result.error,
            )
        )
    return tuple(output)


@trace_call
def write_benchmark_artifact(path: str | Path, store: Any | None = None, artifact_root: str | Path | None = None) -> Path:
    # type-10052026-Maurice: Persist deterministic benchmark JSON without source values.
    target = Path(path)
    records = benchmark(store)
    payload = {
        "catalog_version": "2026-10-05",
        "data_as_of": "2026-01-31",
        "intents": [
            {
                "intent": record.name,
                "cap": record.cap,
                "timeout_seconds": record.timeout_seconds,
                "elapsed_ms": round(record.elapsed_ms, 3),
                "expected_rows": record.expected_rows,
                "result_count": record.result_count,
                "error": record.error.code if record.error else None,
            }
            for record in records
        ],
    }
    if artifact_root is None:
        return write_json_artifact(target.parent, target.name, payload)
    try:
        relative = target.resolve(strict=False).relative_to(Path(artifact_root).resolve(strict=False))
    except ValueError as exc:
        raise ValueError("artifact path escapes root") from exc
    return write_json_artifact(artifact_root, relative.as_posix(), payload)
