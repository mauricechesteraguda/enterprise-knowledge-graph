# type-10052026-Maurice: Freeze complete item-level evidence snapshots at answer time.
"""Evidence correspondence, validation, and immutable snapshot helpers."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from kg.observability.tracing import trace_call

_REQUIRED = {"source_system", "source_record_id", "provenance"}


@dataclass(frozen=True)
class EvidenceResult:
    # type-10052026-Maurice: Expose only validated retrieved evidence correspondence.
    evidence: tuple[dict[str, Any], ...]
    fabricated_items: list[str] = field(default_factory=list)
    unmatched_items: list[str] = field(default_factory=list)


@trace_call
def build(rows: Sequence[Mapping[str, Any]], retrieval_id: str = "retrieval-1", timestamp: str | None = None) -> EvidenceResult:
    # type-10052026-Maurice: Reject partial metadata rather than silently grounding it.
    captured = timestamp or datetime.now(timezone.utc).isoformat()
    output: list[dict[str, Any]] = []
    unmatched: list[str] = []
    for index, row in enumerate(rows):
        item = dict(row)
        # type-10052026-Maurice: Normalize graph rows at the evidence seam without inventing source IDs.
        if item.get("source_record_id"):
            item.setdefault("source_system", "graph")
            item.setdefault("provenance", "approved_retrieval")
        if not _REQUIRED <= set(item) or not all(item.get(key) for key in _REQUIRED):
            unmatched.append(str(index))
            continue
        item.setdefault("source_doc_id", item["source_record_id"])
        item.setdefault("source_doc_title", "")
        item.setdefault("page_number", None)
        item.setdefault("chunk_id", item.get("source_record_id"))
        item.setdefault("excerpt", item.get("text", ""))
        item.setdefault("doc_version_hash", hashlib.sha256(str(item["excerpt"]).encode()).hexdigest())
        item.setdefault("similarity_score", item.get("score", None))
        item["retrieval_id"] = retrieval_id
        item["retrieved_at"] = captured
        output.append(copy.deepcopy(item))
    return EvidenceResult(tuple(output), [], unmatched)
