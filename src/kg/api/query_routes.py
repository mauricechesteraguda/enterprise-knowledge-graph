# type-10052026-Maurice: Keep catalog query route behavior read-only and bounded.
"""Contract seam for GET and POST catalog queries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from kg.observability.tracing import trace_call
from kg.query.catalog import execute


@dataclass(frozen=True)
class QueryRouteResult:
    # type-10052026-Maurice: Expose route metadata without raw query text.
    mutated: bool
    truncated: bool
    rows: tuple[dict[str, str], ...] = ()
    error_code: str | None = None


@trace_call
def dispatch(method: str, *, intent: str, parameters: Mapping[str, str], store: Any | None = None, limit: int = 100, timeout_seconds: int = 5) -> QueryRouteResult:
    # type-10052026-Maurice: Allow only catalog intents for either read-only HTTP method.
    if method not in {"GET", "POST"}:
        return QueryRouteResult(False, False, error_code="method_not_allowed")
    result = execute(intent, parameters, store=store, limit=min(limit, 1000), timeout_seconds=min(timeout_seconds, 5))
    return QueryRouteResult(False, result.truncated, tuple(result.rows), result.error.code if result.error else None)
