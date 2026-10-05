# type-10052026-Maurice: Provide deterministic ground-truth resolution metrics.
"""Ground-truth evaluation for the identity resolver."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kg.identity.resolution import resolve
from kg.observability.tracing import trace_call


@dataclass(frozen=True)
class GroundTruthResult:
    """Precision/recall/F1 and the evaluated assertions."""

    precision: float
    recall: float
    f1: float
    target_f1: float
    true_positive: int
    false_positive: int
    false_negative: int
    assertions: tuple[dict[str, Any], ...]


@trace_call
def ground_truth(target_f1: float = 0.90) -> GroundTruthResult:
    """Evaluate a small committed, deterministic duplicate corpus."""
    people = [
        {"person_id": "person-001", "name": "Juan Dela Cruz", "email": "juan@example.test", "phone": "555010001"},
        {"person_id": "person-002", "name": "Maria Santos", "email": "maria@example.test", "phone": "555010002"},
    ]
    records = [
        {"source_record_id": "crm-001", "name": "Juan Dela Cruz", "email": "juan@example.test", "phone": "555010001"},
        {"source_record_id": "support-001", "name": "Juan Dela Cruz", "email": "juan@example.test"},
        {"source_record_id": "billing-002", "name": "Maria Santos", "email": "maria@example.test", "phone": "555010002"},
    ]
    expected = {"crm-001": "person-001", "support-001": "person-001", "billing-002": "person-002"}
    assertions = tuple(resolve(records, run_id="ground-truth", canonical_persons=people))
    predicted = {item["candidate"]: item["person"] for item in assertions if item["decision"] == "auto_match"}
    tp = sum(predicted.get(key) == value for key, value in expected.items())
    fp = len(predicted) - tp
    fn = len(expected) - tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return GroundTruthResult(round(precision, 6), round(recall, 6), round(f1, 6), target_f1, tp, fp, fn, assertions)
