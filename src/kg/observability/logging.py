# type-10052026-Maurice: Restrict operational events to safe bounded JSON fields.
"""Structured JSON logging with bounded fields and redaction."""
from __future__ import annotations
import json
import logging
import re
import traceback
import hashlib
import math
from collections.abc import Mapping
from typing import Any
from kg.observability.tracing import trace_call
_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization)")
_SECRET_CONTENT = re.compile(r"(?i)\b(?:token|password|api[_-]?key|authorization|bearer|credential|secret)\b\s*(?:[:=]|\s+)+\s*[^,;]+")
_ALLOWED = {"timestamp", "level", "service", "event", "request_id", "run_id", "source", "intent", "elapsed_ms", "outcome", "error_code", "error_class", "operation", "cause", "stack"}
_PII = re.compile(r"(?i)(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|https?://[^\s]+|\+?\d[\d ()-]{7,}\d)")
_CANONICAL = {
    "source": {"billing", "crm", "support", "graph", "graphstore", "source"},
    "intent": {"approved question", "injected_facts", "unpaid_invoices_by_organization", "canonical_identity_records", "orphan_tickets", "cross_silo_unpaid_open_high", "high_priority_products_quarter", "person_account_invoice_product_ticket", "unpaid_invoices", "orphan_ticket"},
}
_MAX_DEPTH = 4
_MAX_ITEMS = 16
_MAX_STRING = 256


@trace_call
def _safe_string(key: str, value: str) -> str:
    # type-10062026-Maurice: Scrub secret patterns in content while preserving stable internal event names.
    bounded = value[:_MAX_STRING]
    if key == "event" and re.fullmatch(r"[a-z][a-z0-9_.-]{1,63}", bounded) and not _SECRET_CONTENT.search(bounded):
        return bounded
    if key in _CANONICAL and bounded not in _CANONICAL[key]:
        return f"hash:{hashlib.sha256(bounded.encode('utf-8')).hexdigest()[:16]}"
    return _PII.sub("<redacted>", _SECRET_CONTENT.sub("<redacted>", bounded))


@trace_call
def _safe_key(key: Any) -> str:
    # type-10062026-Maurice: Coerce and sanitize keys without invoking hostile string conversion.
    if isinstance(key, str):
        try:
            return _safe_string("", key)
        except Exception:
            return "<key>"
    try:
        return f"<{type(key).__name__}>"
    except Exception:
        return "<key>"


@trace_call
def _safe_value(value: Any, depth: int = 0, seen: set[int] | None = None, key: str = "") -> Any:
    # type-10062026-Maurice: Normalize bounded nested data, cycles, secrets, PII, and non-finite numbers.
    if _SECRET.search(key):
        return "<redacted>"
    if depth > _MAX_DEPTH:
        return "<bounded>"
    if seen is None:
        seen = set()
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else ("NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity"))
    if isinstance(value, str):
        try:
            return _safe_string(key, value)
        except Exception:
            return "<redacted>"
    identity = id(value)
    if identity in seen:
        return "<cycle>"
    seen.add(identity)
    try:
        if isinstance(value, Mapping):
            output: dict[str, Any] = {}
            try:
                iterator = iter(value.items())
                for _ in range(_MAX_ITEMS):
                    try:
                        raw_key, item = next(iterator)
                    except StopIteration:
                        break
                    safe_key = _safe_key(raw_key)
                    output[safe_key] = _safe_value(item, depth + 1, seen, safe_key)
            except Exception:
                output["<mapping>"] = "<unavailable>"
            return output
        if isinstance(value, (list, tuple, set, frozenset)):
            output_list: list[Any] = []
            try:
                iterator = iter(value)
                for _ in range(_MAX_ITEMS):
                    try:
                        item = next(iterator)
                    except StopIteration:
                        break
                    output_list.append(_safe_value(item, depth + 1, seen))
            except Exception:
                output_list.append("<unavailable>")
            return output_list
        return f"<{type(value).__name__}>"
    except Exception:
        return "<unavailable>"
    finally:
        seen.discard(identity)


@trace_call
def _safe_fields(fields: dict[str, Any]) -> dict[str, Any]:
    # type-10062026-Maurice: Apply allowlisting before bounded JSON coercion.
    safe: dict[str, Any] = {}
    try:
        items = iter(fields.items())
        for _ in range(_MAX_ITEMS):
            try:
                key, value = next(items)
            except (StopIteration, TypeError):
                break
            if not isinstance(key, str) or key not in _ALLOWED or _SECRET.search(key):
                continue
            safe[key] = _safe_value(value, key=key)
    except Exception:
        return {}
    return safe
class JsonFormatter(logging.Formatter):
    """Serialize an allowlisted event shape; omit raw prompts and PII."""
    @trace_call
    def format(self, record: logging.LogRecord) -> str:
        fields = getattr(record, "event_fields", {})
        safe = _safe_fields(fields if isinstance(fields, dict) else {})
        safe.update({"timestamp": self.formatTime(record), "level": record.levelname, "service": safe.get("service", "knowledge-graph")})
        try:
            return json.dumps(safe, sort_keys=True, allow_nan=False)
        except Exception:
            return '{"event":"logging_serialization_failed"}'
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
    safe = _safe_fields(fields)
    safe["event"] = _safe_string("event", event) if isinstance(event, str) else "event"
    logger.info(safe["event"], extra={"event_fields": safe})


@trace_call
def serialize_event(**fields: Any) -> str:
    # type-10052026-Maurice: Provide a testable redaction seam that drops prompts and secrets.
    safe = _safe_fields(fields)
    try:
        return json.dumps(safe, sort_keys=True, allow_nan=False)
    except Exception:
        return "{}"


@trace_call
def log_exception(logger: logging.Logger, event: str, exc: BaseException, *, operation: str, request_id: str | None = None, run_id: str | None = None, error_code: str | None = None) -> None:
    # type-10062026-Maurice: Emit actionable boundary diagnostics without raw exception text or payloads.
    frames = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else ()
    stack = ">".join(f.name[:64] for f in frames[-4:])[:256]
    cause = type(exc.__cause__).__name__[:80] if exc.__cause__ else None
    log_event(logger, event, operation=operation, request_id=request_id, run_id=run_id, error_class=type(exc).__name__[:80], error_code=(error_code or type(exc).__name__)[:80], cause=cause, stack=stack, outcome="failed")
