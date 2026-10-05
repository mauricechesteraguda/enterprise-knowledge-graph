# type-10052026-Maurice: Provide only foundation health and metrics endpoints.
"""Minimal FastAPI application exposing health and bounded metrics seams."""
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response
from kg.config import get_settings
from kg.observability.logging import configure_logging, get_logger, log_event
from kg.observability.tracing import trace_call
app = FastAPI(title="Enterprise Knowledge Graph", version="0.1.0")
@app.get("/v1/health")
@trace_call
def health() -> dict[str, str]:
    """Report local foundation readiness without credentials."""
    settings = get_settings()
    return {"status": "ok", "environment": settings.environment, "data_as_of": settings.data_as_of.isoformat()}
@app.get("/v1/metrics")
@trace_call
def metrics() -> Response:
    """Expose Prometheus metrics with static labels only."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
@trace_call
def main() -> None:
    """Configure JSON logging for the local API entrypoint."""
    configure_logging()
    log_event(get_logger(__name__), "api_start", outcome="ready")
if __name__ == "__main__":
    main()
