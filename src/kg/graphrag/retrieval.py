# type-10052026-Maurice: Combine approved graph facts and optional vector evidence.
"""Retrieval adapters and a bounded combined retrieval result."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from kg.observability.tracing import trace_call


@dataclass(frozen=True)
class Retrieval:
    # type-10052026-Maurice: Preserve both fact rows and support chunks for auditing.
    facts: tuple[dict[str, Any], ...]
    chunks: tuple[dict[str, Any], ...]
    truncated: bool = False
    error_code: str | None = None


@trace_call
def retrieve(
    intent: str,
    parameters: Mapping[str, str],
    graph_store: Any | None = None,
    vector_store: Any | None = None,
    limit: int = 50,
    timeout_seconds: int = 5,
    question: str = "",
) -> Retrieval:
    # type-10052026-Maurice: Execute only catalog intents and isolate optional vector failure.
    from kg.query.catalog import execute
    graph = execute(intent, parameters, store=graph_store, limit=min(limit, 50), timeout_seconds=timeout_seconds)
    if graph.error:
        return Retrieval((), (), error_code=graph.error.code)
    chunks: tuple[dict[str, Any], ...] = ()
    if vector_store is not None:
        try:
            chunks = tuple(dict(row) for row in vector_store.search(question[:1000], min(limit, 50), timeout_seconds))
        except Exception:
            chunks = ()
    return Retrieval(tuple(dict(row) for row in graph.rows), chunks, graph.truncated)
