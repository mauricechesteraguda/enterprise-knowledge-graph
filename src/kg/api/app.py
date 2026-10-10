# type-10052026-Maurice: Provide versioned, bounded, observable API wiring.
"""Production-oriented HTTP boundary for the knowledge graph service."""
from __future__ import annotations

import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, cast

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from kg.config import Settings, get_settings
from kg.api.auth import authorize
from kg.graphrag.ask import UnsupportedQuestionError, answer
from kg.observability.logging import configure_logging, get_logger, log_event, log_exception
from kg.observability.tracing import trace_call
from kg.observability.metrics import record_stage
from kg.query.catalog import execute

_LOGGER = get_logger(__name__)
_SAFE_OPERATION = re.compile(r"^\s*select\b", re.IGNORECASE)
_REQUESTS = Counter("kg_api_requests_total", "API requests", ("route", "outcome"))


class AskRequest(BaseModel):
    # type-10052026-Maurice: Bound user input before it reaches GraphRAG.
    question: str = Field(min_length=1, max_length=1000)


class SparqlRequest(BaseModel):
    # type-10052026-Maurice: Keep the proxy read-only and bounded.
    query: str = Field(min_length=1, max_length=10_000)
    limit: int = Field(default=100, ge=1, le=1000)
    timeout_seconds: int = Field(default=5, ge=1, le=5)


class ErrorBody(BaseModel):
    # type-10052026-Maurice: Keep all failures machine-readable and non-sensitive.
    code: str
    message: str
    request_id: str


def _request_id(request: Request) -> str:
    # type-10052026-Maurice: Accept safe caller IDs while preventing unbounded headers.
    value = request.headers.get("X-Request-ID", "")
    return value[:80] if re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", value) else str(uuid.uuid4())


@trace_call
def _metric_route(path: str) -> str:
    # type-10052026-Maurice: Collapse paths before labeling metrics to prevent URI cardinality.
    if path.startswith("/v1/ask"):
        return "ask"
    if path.startswith("/v1/sparql"):
        return "sparql"
    if path.startswith("/v1/query"):
        return "query"
    if path.startswith("/health") or path.startswith("/v1/health"):
        return "health"
    if path.startswith("/metrics") or path.startswith("/v1/metrics"):
        return "metrics"
    return "other"


@trace_call
def get_graph_store(request: Request) -> Any:
    # type-10052026-Maurice: Resolve GraphStore through application state for injected fakes.
    return request.app.state.graph_store


@trace_call
def get_vector_store(request: Request) -> Any:
    # type-10052026-Maurice: Resolve optional VectorStore through application state.
    return request.app.state.vector_store


@trace_call
def get_llm(request: Request) -> Any:
    # type-10052026-Maurice: Resolve LLM through application state without provider coupling.
    return request.app.state.llm


@trace_call
def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    # type-10052026-Maurice: Enforce explicit opt-in authentication without logging credentials.
    result = authorize(x_api_key, expected=request.app.state.settings.api_key)
    if result.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=result.status_code, detail=result.code)


@trace_call
def _error(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    # type-10052026-Maurice: Return the stable envelope and generated correlation ID.
    return JSONResponse({"error": {"code": code, "message": message, "request_id": request.state.request_id}}, status_code=status_code)


@trace_call
def _sparql_allowed(query: str) -> bool:
    # type-10052026-Maurice: Reject updates, multiple operations, and comments before execution.
    upper = query.upper()
    return bool(_SAFE_OPERATION.match(query)) and not any(token in upper for token in (";", "INSERT", "DELETE", "DROP", "CLEAR", "LOAD", "CREATE", "WITH", "MOVE", "COPY", "ADD"))


@trace_call
def create_app(*, settings: Settings | None = None, graph_store: Any | None = None, vector_store: Any | None = None, llm: Any | None = None) -> FastAPI:
    # type-10052026-Maurice: Build an injectable app for production adapters and contract fakes.
    from kg.query.catalog import RDFLibGraphStore
    configured = settings or get_settings()
    application = FastAPI(title="Enterprise Knowledge Graph", version="1.0.0")
    application.state.settings = configured
    application.state.graph_store = graph_store or RDFLibGraphStore()
    application.state.vector_store = vector_store
    application.state.llm = llm
    static_dir = Path.cwd() / "static"
    if static_dir.is_dir():
        application.mount("/static", StaticFiles(directory=static_dir), name="static")
    application.add_middleware(CORSMiddleware, allow_origins=getattr(configured, "cors_origins", []), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"])

    @application.get("/", include_in_schema=False)
    @trace_call
    async def dashboard() -> FileResponse:
        # type-10052026-Maurice: Serve the static operator surface without store access.
        return FileResponse(Path.cwd() / "static" / "index.html")

    @application.middleware("http")
    @trace_call
    async def correlation(request: Request, call_next: Callable[..., Any]) -> Response:
        # type-10052026-Maurice: Attach a bounded request ID and never record request content.
        request.state.request_id = _request_id(request)
        started = time.monotonic()
        try:
            response = cast(Response, await call_next(request))
        except Exception:
            _REQUESTS.labels(_metric_route(request.url.path), "exception").inc()
            raise
        response.headers["X-Request-ID"] = request.state.request_id
        _REQUESTS.labels(_metric_route(request.url.path), "success" if response.status_code < 400 else "error").inc()
        record_stage("provider", "success" if response.status_code < 400 else "failed", time.monotonic() - started)
        log_event(_LOGGER, "api_request", request_id=request.state.request_id, outcome="success" if response.status_code < 400 else "error", elapsed_ms=round((time.monotonic() - started) * 1000, 2))
        return response

    @application.exception_handler(RequestValidationError)
    @trace_call
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # type-10052026-Maurice: Normalize Pydantic failures without reflecting body values.
        log_event(_LOGGER, "api_validation_failed", request_id=request.state.request_id, operation="request_validation", outcome="failed", error_code="validation_error")
        return _error(request, "validation_error", "request validation failed", 422)

    @application.exception_handler(HTTPException)
    @trace_call
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        # type-10052026-Maurice: Normalize authentication and route errors.
        code = str(exc.detail) if isinstance(exc.detail, str) and re.fullmatch(r"[a-z_]+", exc.detail) else "http_error"
        log_event(_LOGGER, "api_http_failed", request_id=request.state.request_id, operation="http_boundary", outcome="failed", error_code=code)
        return _error(request, code, "request rejected", exc.status_code)

    @application.exception_handler(Exception)
    @trace_call
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        # type-10052026-Maurice: Fail closed while keeping exception details out of responses/logs.
        log_exception(_LOGGER, "api_exception", exc, operation="api.request", request_id=request.state.request_id, error_code="internal_error")
        return _error(request, "internal_error", "internal server error", 500)

    @application.get("/health/live")
    @trace_call
    async def live() -> dict[str, str]:
        # type-10052026-Maurice: Provide a dependency-free liveness probe.
        return {"status": "ok"}

    @application.get("/health/ready", response_model=None)
    @application.get("/v1/health", response_model=None)
    @trace_call
    async def ready(request: Request) -> Response | dict[str, Any]:
        # type-10052026-Maurice: Distinguish required graph failure from optional provider degradation.
        store = application.state.graph_store
        required = "ok"
        try:
            checker = getattr(store, "health", None)
            if checker and checker() is False:
                required = "failed"
                log_event(_LOGGER, "api_readiness_failed", request_id=request.state.request_id, operation="api.readiness", outcome="failed", error_code="graph_unavailable")
        except Exception as exc:
            required = "failed"
            log_exception(_LOGGER, "api_readiness_failed", exc, operation="api.readiness", request_id=getattr(request.state, "request_id", None), error_code="graph_unavailable")
        optional = {"vector": "ok" if application.state.vector_store is not None else "degraded", "llm": "ok" if application.state.llm is not None else "degraded"}
        payload = {"status": "ok" if required == "ok" else "failed", "required": {"graph": required}, "optional": optional, "data_as_of": application.state.settings.data_as_of.isoformat()}
        if required != "ok":
            return JSONResponse(status_code=503, content=payload)
        return payload

    @application.get("/metrics")
    @application.get("/v1/metrics")
    @trace_call
    async def metrics() -> Response:
        # type-10052026-Maurice: Expose Prometheus output with bounded route and outcome labels.
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @application.post("/v1/ask", dependencies=[Depends(require_api_key)])
    @trace_call
    async def ask_endpoint(request: Request, body: AskRequest, store: Any = Depends(get_graph_store), vector: Any = Depends(get_vector_store), provider: Any = Depends(get_llm)) -> dict[str, Any]:
        # type-10052026-Maurice: Return typed GraphRAG output and stable audit metadata.
        try:
            result = answer(body.question, graph_store=store, vector_store=vector, provider=provider, max_evidence=application.state.settings.max_evidence_rows, request_id=request.state.request_id)
        except UnsupportedQuestionError:
            raise HTTPException(422, "unsupported_question")
        return {"answer": result.answer, "grounding_status": result.grounding_status, "evidence_snapshot_id": result.evidence_snapshot_id, "data_as_of": application.state.settings.data_as_of.isoformat(), "provider_status": result.provider_status, "truncated": result.truncated, "linked_entities": [], "request_id": request.state.request_id}

    @application.get("/v1/sparql", dependencies=[Depends(require_api_key)])
    @trace_call
    async def sparql_get(request: Request, query: str = Query(max_length=10_000), limit: int = Query(default=100, ge=1, le=1000), timeout_seconds: int = Query(default=5, ge=1, le=5), store: Any = Depends(get_graph_store)) -> dict[str, Any]:
        # type-10052026-Maurice: Route bounded read-only GET queries through the store seam.
        return await _run_sparql(query, limit, timeout_seconds, store, request.state.request_id)

    @application.post("/v1/sparql", dependencies=[Depends(require_api_key)])
    @trace_call
    async def sparql_post(request: Request, body: SparqlRequest, store: Any = Depends(get_graph_store)) -> dict[str, Any]:
        # type-10052026-Maurice: Route bounded read-only POST queries through the same policy.
        return await _run_sparql(body.query, body.limit, body.timeout_seconds, store, request.state.request_id)

    @application.get("/v1/entities", dependencies=[Depends(require_api_key)])
    @trace_call
    async def entities(page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100), store: Any = Depends(get_graph_store)) -> dict[str, Any]:
        # type-10052026-Maurice: Serve bounded dashboard pagination without exposing raw graph access.
        if hasattr(store, "list_entities"):
            rows = list(store.list_entities(offset=(page - 1) * page_size, limit=page_size + 1))
            items = rows[:page_size]
        else:
            rows = list(store.entities(limit=page * page_size) if hasattr(store, "entities") else [])
            start = (page - 1) * page_size
            items = rows[start:start + page_size]
        return {"items": items, "page": page, "page_size": page_size, "has_more": len(rows) > page_size}

    @application.get("/v1/query", dependencies=[Depends(require_api_key)])
    @trace_call
    async def catalog_query(request: Request, intent: str, limit: int = Query(default=100, ge=1, le=1000), timeout_seconds: int = Query(default=5, ge=1, le=5), store: Any = Depends(get_graph_store)) -> dict[str, Any]:
        # type-10052026-Maurice: Expose only the existing read-only catalog, never arbitrary text.
        result = execute(intent, {}, store=store, limit=limit, timeout_seconds=timeout_seconds, request_id=request.state.request_id)
        if result.error:
            raise HTTPException(400, result.error.code)
        return {"intent": result.intent, "rows": list(result.rows), "truncated": result.truncated, "elapsed_ms": result.elapsed_ms}

    @application.get("/v1/stats", dependencies=[Depends(require_api_key)])
    @application.get("/v1/system/stats", dependencies=[Depends(require_api_key)])
    @trace_call
    async def stats() -> dict[str, Any]:
        # type-10052026-Maurice: Expose bounded dashboard counters only.
        store = application.state.graph_store
        value = store.system_stats() if hasattr(store, "system_stats") else (store.stats() if hasattr(store, "stats") else {})
        return {"stats": {str(k)[:64]: int(v) for k, v in value.items() if isinstance(v, (int, float))}}

    @trace_call
    async def _run_sparql(query: str, limit: int, timeout_seconds: int, store: Any, request_id: str | None = None) -> dict[str, Any]:
        # type-10052026-Maurice: Enforce read-only policy before any adapter invocation.
        if not _sparql_allowed(query):
            log_event(_LOGGER, "api_validation_failed", request_id=request_id, operation="sparql_policy", outcome="failed", error_code="sparql_operation_not_allowed")
            raise HTTPException(400, "sparql_operation_not_allowed")
        runner = getattr(store, "sparql", None)
        if runner is not None:
            materialized = list(runner(query, limit=limit + 1, timeout_seconds=timeout_seconds))
            return {"rows": materialized[:limit], "truncated": len(materialized) > limit}
        log_event(_LOGGER, "api_http_failed", request_id=request_id, operation="sparql_adapter", outcome="failed", error_code="sparql_operation_not_allowed")
        raise HTTPException(400, "sparql_operation_not_allowed")

    return application


configure_logging()
app = create_app()


@trace_call
def main() -> None:
    # type-10052026-Maurice: Configure safe JSON logging for the API entrypoint.
    configure_logging()
    log_event(get_logger(__name__), "api_start", outcome="ready")
