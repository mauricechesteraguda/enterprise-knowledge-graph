# type-10052026-Maurice: Keep canonical identity URI construction deterministic and source-safe.
"""Stable URI rules for canonical and source-derived resources."""
from __future__ import annotations

import re
from urllib.parse import quote

from kg.observability.logging import log_event, get_logger
from kg.observability.tracing import trace_call

BASE_URI = "https://example.org/kg"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~-]*$")
_LOGGER = get_logger(__name__)


# type-10052026-Maurice: Reject ambiguous identifiers instead of silently changing identity.
@trace_call
def canonical_uri(class_name: str, identifier: str) -> str:
    """Return the stable URI for a canonical class and identifier."""
    try:
        if not class_name or not identifier or "/" in class_name:
            raise ValueError("class and identifier are required")
        encoded_class = quote(class_name, safe="")
        if not _SAFE_ID.fullmatch(identifier):
            raise ValueError("identifier contains unsupported characters")
        result = f"{BASE_URI}/{encoded_class}/{identifier}"
        log_event(_LOGGER, "canonical_uri_created", outcome="success")
        return result
    except Exception:
        log_event(_LOGGER, "canonical_uri_rejected", outcome="failed", error_code="invalid_identifier")
        raise


# type-10052026-Maurice: Keep source records in a distinct namespace from canonical entities.
@trace_call
def source_record_uri(source_system: str, record_id: str) -> str:
    """Return a URI that cannot masquerade as a canonical person."""
    if not source_system or not record_id or not _SAFE_ID.fullmatch(source_system) or not _SAFE_ID.fullmatch(record_id):
        raise ValueError("source system and record ID must be safe identifiers")
    return f"{BASE_URI}/SourceRecord/{source_system}/{record_id}"
