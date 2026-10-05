# type-10052026-Maurice: Restrict operational events to safe bounded JSON fields.
"""Structured JSON logging with bounded fields and redaction."""
from __future__ import annotations
import json
import logging
import re
from typing import Any
from kg.observability.tracing import trace_call
_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization)")
_ALLOWED = {"timestamp", "level", "service", "event", "request_id", "run_id", "source", "intent", "elapsed_ms", "outcome", "error_code"}
class JsonFormatter(logging.Formatter):
    """Serialize an allowlisted event shape; omit raw prompts and PII."""
    @trace_call
    def format(self, record: logging.LogRecord) -> str:
        fields = getattr(record, "event_fields", {})
        safe = {key: value for key, value in fields.items() if key in _ALLOWED and not _SECRET.search(key)}
        safe.update({"timestamp": self.formatTime(record), "level": record.levelname, "service": safe.get("service", "knowledge-graph")})
        return json.dumps(safe, sort_keys=True)
@trace_call
def configure_logging(level: str = "INFO") -> None:
    """Configure one JSON stream handler for application logs."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
@trace_call
def get_logger(name: str) -> logging.Logger:
    """Return a logger for bounded event fields."""
    return logging.getLogger(name)
@trace_call
def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit an allowlisted structured event without unrestricted text."""
    safe = {key: value for key, value in fields.items() if key in _ALLOWED}
    safe["event"] = event
    logger.info(event, extra={"event_fields": safe})


@trace_call
def serialize_event(**fields: Any) -> str:
    # type-10052026-Maurice: Provide a testable redaction seam that drops prompts and secrets.
    safe = {key: value for key, value in fields.items() if key in _ALLOWED and not _SECRET.search(key)}
    return json.dumps(safe, sort_keys=True)
