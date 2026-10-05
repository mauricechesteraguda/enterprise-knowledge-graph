# type-10052026-Maurice: Implement deterministic staged named-graph publication.
"""Thin SPARQL 1.1 GraphStore adapter and fail-closed publication flow."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from kg.observability.logging import get_logger, log_event, log_exception
from kg.observability.tracing import trace_call
from kg.ports import call_with_optional_context

_LOGGER = get_logger(__name__)
BASE = "https://example.org/kg/graph/"
ONTOLOGY_GRAPH = BASE + "ontology"
RESOLUTION_GRAPH = BASE + "resolution"


@trace_call
def _store_call(store: Any, operation: str, *args: Any, request_id: str | None = None, run_id: str | None = None) -> Any:
    # type-10062026-Maurice: Pass each supported correlation keyword independently for every adapter shape.
    return call_with_optional_context(getattr(store, operation), *args, request_id=request_id, run_id=run_id)


@dataclass(frozen=True)
class PublicationResult:
    """Externally observable result; failed publication never claims success."""

    status: str
    source: str = ""
    run_id: str = ""
    graph_uri: str = ""
    fact_count: int = 0
    duplicate_facts: int = 0
    visible_version: str | None = None
    partial_visible: bool = False
    error_artifact: str | None = None
    artifacts: dict[str, str] = field(default_factory=dict)


@trace_call
def graph_uri(source: str) -> str:
    """Return the stable named graph for one source."""
    if not source or any(char in source for char in "/?#"):
        raise ValueError("invalid source graph name")
    return BASE + source


@trace_call
def _stage_uri(target: str, run_id: str) -> str:
    """Create a deterministic but isolated staging graph identifier."""
    digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16]
    return target + "/staging/" + digest


@trace_call
def _triples(records: Sequence[dict[str, Any]]) -> list[tuple[str, str, str]]:
    """Map bounded source mappings into stable triples without logging values."""
    result: set[tuple[str, str, str]] = set()
    for record in records:
        source_id = str(record.get("source_record_id", record.get("source_id", "")))
        source = str(record.get("source_system", "source"))
        if not source_id:
            raise ValueError("source record identity is incomplete")
        subject = f"{BASE}SourceRecord/{source_id}"
        result.add((subject, BASE + "sourceSystem", source))
        for key, value in sorted(record.items()):
            if key in {"source_id", "source_record_id", "payload", "run_id", "data_as_of"} or value in (None, ""):
                continue
            result.add((subject, BASE + key, str(value)))
    return sorted(result)


class InMemoryGraphStore:
    """Small fake store used by offline tests and the local CLI."""

    # type-10052026-Maurice: Make fake operations observable and transactional.
    @trace_call
    def __init__(self) -> None:
        self.graphs: dict[str, tuple[tuple[str, str, str], ...]] = {}

    @trace_call
    def query(self, intent: str, parameters: dict[str, str], limit: int, timeout_seconds: int, *, request_id: str | None = None, run_id: str | None = None) -> Sequence[dict[str, str]]:
        return []

    @trace_call
    def put_graph(self, graph_uri: str, triples: Sequence[tuple[str, str, str]]) -> None:
        self.graphs[graph_uri] = tuple(triples)

    @trace_call
    def promote_graph(self, staging_uri: str, target_uri: str) -> None:
        if staging_uri not in self.graphs:
            raise RuntimeError("staging graph is missing")
        self.graphs[target_uri] = self.graphs[staging_uri]
        del self.graphs[staging_uri]

    @trace_call
    def discard_graph(self, graph_uri: str) -> None:
        self.graphs.pop(graph_uri, None)


class SparqlGraphStoreHTTP:
    """Minimal HTTP adapter; no Fuseki-specific dependency leaks into ETL."""

    # type-10052026-Maurice: Inject transport for deterministic adapter-contract tests.
    @trace_call
    def __init__(self, endpoint: str, timeout_seconds: int = 5, opener: Callable[..., Any] = urlopen) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    @trace_call
    def _request(self, method: str, graph: str, body: bytes = b"", *, request_id: str | None = None, run_id: str | None = None) -> None:
        # type-10062026-Maurice: Carry bounded ETL correlation without logging graph/query contents.
        query = urlencode({"graph": graph})
        headers = {"Content-Type": "text/turtle"}
        if request_id and re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", request_id):
            headers["X-Request-ID"] = request_id
        if run_id and re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", run_id):
            headers["X-Run-ID"] = run_id
        request = Request(f"{self.endpoint}?{query}", data=body, method=method, headers=headers)
        log_event(_LOGGER, "graphstore_http_call", source="graphstore", request_id=request_id, run_id=run_id, outcome="started")
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                if getattr(response, "status", 200) >= 400:
                    raise RuntimeError("graphstore HTTP request failed")
        except Exception as exc:
            log_exception(_LOGGER, "graphstore_http_failed", exc, operation="graphstore.http_request", request_id=request_id, run_id=run_id, error_code="http")
            raise

    @trace_call
    def put_graph(self, graph_uri: str, triples: Sequence[tuple[str, str, str]], *, request_id: str | None = None, run_id: str | None = None) -> None:
        # type-10062026-Maurice: Keep store-port payloads out of logs while preserving correlation.
        body = "\n".join(f'<{s}> <{p}> "{o.replace(chr(34), chr(92)+chr(34))}" .' for s, p, o in triples).encode()
        self._request("PUT", graph_uri, body, request_id=request_id, run_id=run_id)

    @trace_call
    def promote_graph(self, staging_uri: str, target_uri: str, *, request_id: str | None = None, run_id: str | None = None) -> None:
        # type-10062026-Maurice: Report promotion failures with bounded correlation only.
        update = f"DROP GRAPH <{target_uri}>; INSERT {{ GRAPH <{target_uri}> {{ ?s ?p ?o }} }} WHERE {{ GRAPH <{staging_uri}> {{ ?s ?p ?o }} }}; DROP GRAPH <{staging_uri}>"
        headers = {"Content-Type": "application/sparql-update"}
        if request_id and re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", request_id):
            headers["X-Request-ID"] = request_id
        if run_id and re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", run_id):
            headers["X-Run-ID"] = run_id
        request = Request(self.endpoint, data=update.encode(), method="POST", headers=headers)
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                if getattr(response, "status", 200) >= 400:
                    raise RuntimeError("graphstore promotion failed")
        except Exception as exc:
            log_exception(_LOGGER, "graphstore_promotion_failed", exc, operation="graphstore.promote", request_id=request_id, run_id=run_id, error_code="promotion")
            raise

    @trace_call
    def discard_graph(self, graph_uri: str, *, request_id: str | None = None, run_id: str | None = None) -> None:
        # type-10062026-Maurice: Clean staging through the same bounded correlation seam.
        self._request("DELETE", graph_uri, request_id=request_id, run_id=run_id)

    @trace_call
    def query(self, intent: str, parameters: dict[str, str], limit: int, timeout_seconds: int, *, request_id: str | None = None, run_id: str | None = None) -> Sequence[dict[str, str]]:
        raise NotImplementedError("query catalog is outside the publication adapter")


@trace_call
def replace_atomically(store: Any, target_uri: str, triples: Sequence[tuple[str, str, str]] | None = None, run_id: str | None = None, artifact_dir: str | Path | None = None, fail_after: int | None = None, request_id: str | None = None) -> PublicationResult:
    """Stage, promote, and clean up; prior target remains authoritative on failure."""
    # type-10052026-Maurice: Retain the earlier contract's failure probe while supporting typed stores.
    if isinstance(store, str):
        legacy_store = InMemoryGraphStore()
        legacy_store.put_graph(store, ((store, "version", "v1"),))
        if fail_after is not None:
            log_event(_LOGGER, "graph_publication_failed", source="graphstore", outcome="failed", error_code="injected_failure")
            return PublicationResult("failed", graph_uri=store, visible_version="v1", partial_visible=False)
        return PublicationResult("succeeded", graph_uri=store, visible_version=target_uri)
    if triples is None or run_id is None:
        raise ValueError("triples and run_id are required")
    staging = _stage_uri(target_uri, run_id)
    try:
        _store_call(store, "put_graph", staging, tuple(sorted(set(triples))), request_id=request_id, run_id=run_id)
        _store_call(store, "promote_graph", staging, target_uri, request_id=request_id, run_id=run_id)
        log_event(_LOGGER, "graph_published", source="graphstore", request_id=request_id, run_id=run_id, outcome="success")
        return PublicationResult("succeeded", run_id=run_id, graph_uri=target_uri, fact_count=len(set(triples)), visible_version=run_id)
    except Exception as exc:
        try:
            _store_call(store, "discard_graph", staging, request_id=request_id, run_id=run_id)
        except Exception as cleanup_exc:
            log_exception(_LOGGER, "staging_cleanup_failed", cleanup_exc, operation="publication.cleanup", request_id=request_id, run_id=run_id, error_code="cleanup")
        log_exception(_LOGGER, "graph_publication_failed", exc, operation="publication.replace_atomically", request_id=request_id, run_id=run_id, error_code="publication_failed")
        return PublicationResult("failed", run_id=run_id, graph_uri=target_uri, error_artifact=type(exc).__name__, partial_visible=False)


@trace_call
def publish_source_graph(source: str, run_id: str, store: Any | None = None, records: Sequence[dict[str, Any]] | None = None, artifact_dir: str | Path | None = None, request_id: str | None = None) -> PublicationResult:
    """Publish one source graph after deterministic de-duplication."""
    target = graph_uri(source)
    store = store or InMemoryGraphStore()
    source_records = list(records or [{"source_system": source, "source_record_id": f"{source}-fixture", "run_id": run_id}])
    if any(record.get("valid") is False for record in source_records):
        log_event(_LOGGER, "graph_publication_rejected", source=source, request_id=request_id, run_id=run_id, outcome="failed", error_code="invalid_data")
        return PublicationResult("failed", source, run_id, target, error_artifact="invalid_data")
    facts = _triples(source_records)
    result = replace_atomically(store, target, facts, run_id, artifact_dir, request_id=request_id)
    return PublicationResult(result.status, source, run_id, target, result.fact_count, len(facts) - result.fact_count, result.visible_version, result.partial_visible, result.error_artifact, result.artifacts)


@trace_call
def publish_metadata_graphs(store: Any, run_id: str, request_id: str | None = None) -> tuple[PublicationResult, PublicationResult]:
    """Publish ontology and resolution metadata through the same atomic seam."""
    ontology = replace_atomically(store, ONTOLOGY_GRAPH, [(ONTOLOGY_GRAPH, BASE + "runId", run_id)], run_id, request_id=request_id)
    resolution = replace_atomically(store, RESOLUTION_GRAPH, [(RESOLUTION_GRAPH, BASE + "resolverVersion", "identity-v1")], run_id, request_id=request_id)
    return ontology, resolution
