# type-10052026-Maurice: Normalize API validation failures into a stable envelope.
"""Non-sensitive error response boundary for malformed API requests."""
from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from kg.observability.tracing import trace_call


class ErrorMapping(dict[str, Any]):
    # type-10052026-Maurice: Support field-set contract checks while remaining JSON-compatible.

    @trace_call
    def __ge__(self, other: object) -> bool:
        # type-10052026-Maurice: Compare envelope fields without reflecting invalid input values.
        if isinstance(other, set):
            return other <= set(self.keys())
        return False


@trace_call
def validate_error(payload: Mapping[str, Any], request_id: str | None = None) -> ErrorMapping:
    # type-10052026-Maurice: Return bounded validation metadata and never echo request contents.
    details = {"fields": tuple(sorted(str(key)[:64] for key in payload.keys()))}
    return ErrorMapping({"error": ErrorMapping({"code": "validation_error", "message": "request validation failed", "details": details}), "request_id": request_id or str(uuid4())})
