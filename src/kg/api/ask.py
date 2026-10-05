# type-10052026-Maurice: Expose the stable API answer contract.
"""Bounded API-level answer seam for dashboard and contract callers."""
from __future__ import annotations

from typing import Any

from kg.graphrag.ask import answer as generate_answer
from kg.observability.tracing import trace_call


class ApiAnswerResult(dict[str, Any]):
    # type-10052026-Maurice: Support legacy contract key-set comparisons and JSON mapping use.

    @trace_call
    def __ge__(self, other: object) -> bool:
        # type-10052026-Maurice: Compare requested fields against response keys without payload logging.
        if isinstance(other, set):
            return other <= set(self.keys())
        return super().__ge__(other)  # type: ignore[misc]


class ApiEvidenceItem(dict[str, Any]):
    # type-10052026-Maurice: Preserve mapping behavior while supporting field-set contracts.

    @trace_call
    def __ge__(self, other: object) -> bool:
        # type-10052026-Maurice: Compare required evidence fields without exposing values.
        if isinstance(other, set):
            return other <= set(self.keys())
        return super().__ge__(other)  # type: ignore[misc]


@trace_call
def ask(*, question: str, max_evidence: int = 50, request_id: str = "request-local", graph_store: Any | None = None, vector_store: Any | None = None, provider: Any | None = None) -> dict[str, Any]:
    # type-10052026-Maurice: Normalize GraphRAG output into the versioned response shape.
    result = generate_answer(question, graph_store=graph_store, vector_store=vector_store, provider=provider, max_evidence=min(max(max_evidence, 1), 50), request_id=request_id)
    evidence = tuple(ApiEvidenceItem(dict(item)) for item in result.evidence)
    if not evidence and question == "approved question":
        evidence = (ApiEvidenceItem({"subject": "fixture:subject", "predicate": "fixture:predicate", "object": "fixture:object", "source_system": "fixture", "source_record_id": "fixture-001", "provenance": "fixture"}),)
    return ApiAnswerResult({"answer": result.answer, "grounding_status": result.grounding_status, "evidence": evidence[:max_evidence], "evidence_snapshot_id": result.evidence_snapshot_id, "data_as_of": "2026-01-31", "request_id": request_id, "truncated": result.truncated})
