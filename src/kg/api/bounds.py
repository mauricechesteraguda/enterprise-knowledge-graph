# type-10052026-Maurice: Centralize request and result limits for API contracts.
"""Pure bounded-input validation with no access to request content in logs."""
from __future__ import annotations

from dataclasses import dataclass

from kg.observability.tracing import trace_call


@dataclass(frozen=True)
class BoundsResult:
    # type-10052026-Maurice: Return normalized timeout and acceptance metadata.
    accepted: bool
    timeout_seconds: int
    max_evidence: int


@trace_call
def validate_request(*, question: str, max_evidence: int = 50, timeout_seconds: int = 5) -> BoundsResult:
    # type-10052026-Maurice: Enforce fixed caps before provider or store calls.
    bounded_timeout = min(max(int(timeout_seconds), 1), 5)
    accepted = isinstance(question, str) and 1 <= len(question) <= 1000 and 1 <= max_evidence <= 50 and 1 <= timeout_seconds <= 5
    return BoundsResult(accepted, bounded_timeout, min(max(int(max_evidence), 0), 50))
