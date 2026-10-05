# type-10052026-Maurice: Define the explicit API-key authentication seam.
"""Small, provider-neutral API-key policy used by HTTP dependencies and tests."""
from __future__ import annotations

import hmac
from dataclasses import dataclass

from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

_LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class AuthorizationResult:
    # type-10052026-Maurice: Keep auth outcomes typed without retaining credentials.
    status_code: int
    status: str
    code: str
    message: str


@trace_call
def authorize(provided: str | None, *, expected: str | None) -> AuthorizationResult:
    # type-10052026-Maurice: Make local auth opt-in and compare configured secrets in constant time.
    if not expected:
        result = AuthorizationResult(200, "disabled_explicit", "auth_disabled", "authentication disabled")
    elif provided is None:
        result = AuthorizationResult(401, "unauthorized", "missing_api_key", "authentication required")
    elif hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        result = AuthorizationResult(200, "authorized", "authorized", "authorized")
    else:
        result = AuthorizationResult(403, "forbidden", "invalid_api_key", "invalid credentials")
    # type-10052026-Maurice: Emit only bounded outcome metadata; never log key material.
    log_event(_LOGGER, "api_auth", outcome=result.status)
    return result


@trace_call
def mode_result(*, required: bool, key: str | None) -> AuthorizationResult:
    # type-10052026-Maurice: Represent configuration mode explicitly for operators and contracts.
    if not required:
        return AuthorizationResult(200, "disabled_explicit", "auth_disabled", "authentication disabled")
    if not key:
        return AuthorizationResult(401, "unauthorized", "missing_api_key", "authentication required")
    return authorize(None, expected=key)
