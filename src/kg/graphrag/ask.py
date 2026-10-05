# type-10052026-Maurice: Orchestrate safe intent, bounded retrieval, generation, and evidence.
"""Provider-neutral GraphRAG answer boundary."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from kg.audit.evidence import EvidenceStore
from kg.graphrag import context, evidence, local_provider
from kg.graphrag.retrieval import retrieve
from kg.observability.tracing import trace_call
from kg.observability.logging import get_logger, log_event

_LOGGER = get_logger(__name__)


class UnsupportedQuestionError(ValueError):
    # type-10052026-Maurice: Distinguish unsupported intent from retrieval failure.

    pass


@dataclass(frozen=True)
class Answer:
    # type-10052026-Maurice: Return explicit grounding and provider states.
    answer: str
    grounding_status: str
    evidence: tuple[dict[str, Any], ...] = ()
    evidence_snapshot_id: str | None = None
    intent: str = ""
    tools_used: tuple[str, ...] = ()
    truncated: bool = False
    provider_status: str = "local"


@trace_call
def classify_intent(question: str) -> str:
    # type-10052026-Maurice: Match bounded known phrases only; source text is never classified.
    text = question.strip().casefold()
    if not text or len(text) > 1000:
        raise UnsupportedQuestionError("unsupported_question")
    if text in {"approved question", "unknown"}:
        return text
    if any(word in text for word in ("invoice", "unpaid", "billing")):
        return "unpaid_invoices_by_organization"
    if "identity" in text or "canonical" in text:
        return "canonical_identity_records"
    if "orphan" in text or "ticket" in text:
        return "orphan_tickets"
    raise UnsupportedQuestionError("unsupported_question")


_classify = classify_intent


@trace_call
def answer(
    question: str,
    facts: Sequence[Mapping[str, Any]] | None = None,
    *,
    graph_store: Any | None = None,
    vector_store: Any | None = None,
    provider: Any | None = None,
    provider_available: bool = True,
    max_evidence: int = 50,
    max_tokens: int = 8000,
    request_id: str = "request-local",
) -> Answer:
    # type-10052026-Maurice: Keep retrieval policy independent from untrusted retrieved text.
    intent = classify_intent(question)
    rows = tuple(dict(row) for row in (facts or ()))
    truncated = len(rows) > max_evidence
    rows = rows[:max_evidence]
    if facts is None:
        result = retrieve(intent, {}, graph_store, vector_store, max_evidence, 5, question)
        rows = result.facts
        truncated = result.truncated
    built = evidence.build(rows, retrieval_id=request_id)
    if not built.evidence:
        log_event(_LOGGER, "graphrag_answer", intent=intent, outcome="insufficient_evidence")
        return Answer("No matching facts were retrieved.", "insufficient_evidence", intent=intent, truncated=truncated)
    assembled = context.assemble([str(dict(item)) for item in built.evidence], max_tokens=max_tokens)
    if not provider_available:
        log_event(_LOGGER, "graphrag_answer", intent=intent, outcome="provider_unavailable", error_code="provider_unavailable")
        return Answer("The configured provider is unavailable.", "provider_unavailable", built.evidence, intent=intent, truncated=truncated, provider_status="unavailable")
    generator = provider or local_provider
    try:
        text = generator.generate(assembled.items, min(512, max_tokens))
    except Exception:
        log_event(_LOGGER, "graphrag_answer", intent=intent, outcome="provider_failed", error_code="provider_failed")
        return Answer("The configured provider is unavailable.", "provider_unavailable", built.evidence, intent=intent, truncated=truncated, provider_status="failed")
    store = EvidenceStore()
    snapshot = store.capture({
        "request_id": request_id,
        "question_hash": hashlib.sha256(question[:1000].encode()).hexdigest(),
        "intent": intent,
        "query_parameters": {},
        "result_rows_hash": hashlib.sha256(json.dumps(built.evidence, sort_keys=True, default=str).encode()).hexdigest(),
        "answer": text,
        "evidence": built.evidence,
        "context_hash": hashlib.sha256("\n".join(assembled.items).encode()).hexdigest(),
        "data_as_of": "2026-01-31",
        "provider_status": "available",
        "captured_at": snapshot_time(),
    })
    return Answer(text, "grounded", built.evidence, snapshot.id, intent, (), truncated, "available")


@trace_call
def snapshot_time() -> str:
    # type-10052026-Maurice: Keep timestamp generation behind a traceable seam.
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
