# type-10052026-Maurice: Define the minimum provenance contract shared by every source-derived resource.
"""Provenance vocabulary constants and validation helpers."""
from __future__ import annotations

from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

REQUIRED_FIELDS = frozenset({"source_system", "source_record", "provenance", "run_id", "data_as_of"})
_LOGGER = get_logger(__name__)


# type-10052026-Maurice: Return a copy so callers cannot mutate the governance contract.
@trace_call
def required_fields() -> set[str]:
    """Return mandatory source provenance field names."""
    log_event(_LOGGER, "provenance_contract_read", outcome="success")
    return set(REQUIRED_FIELDS)
