# type-10052026-Maurice: Define the dashboard's small, observable rendering seam.
"""Contracts shared by the static dashboard and its operational checks."""
from __future__ import annotations

from dataclasses import dataclass

from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

_LOGGER = get_logger(__name__)
_REQUIRED_API_VIEWS = ("health", "etl", "resolution", "query", "evidence")


@dataclass(frozen=True)
class DashboardState:
    """Bounded state used to render loading, error, and usable dashboard views."""

    visible_status: str
    message: str


@trace_call
def required_api_views() -> tuple[str, ...]:
    # type-10052026-Maurice: Keep dashboard dependencies versioned and explicit.
    views = tuple(_REQUIRED_API_VIEWS)
    log_event(_LOGGER, "dashboard_contract_checked", outcome="success")
    return views


@trace_call
def state(*, health: str = "ready") -> DashboardState:
    # type-10052026-Maurice: Map dependency responses to visible, non-sensitive UI states.
    normalized = health.strip().lower()
    if normalized in {"loading", "pending"}:
        result = DashboardState("loading", "Checking service health")
    elif normalized in {"503", "error", "failed", "unavailable"}:
        result = DashboardState("error", "A required service is unavailable")
    elif normalized in {"empty", "no_data"}:
        result = DashboardState("empty", "No graph data is available yet")
    elif normalized in {"unsupported", "unsupported_question"}:
        result = DashboardState("unsupported", "This question is outside the supported graph catalog")
    else:
        result = DashboardState("ready", "Dashboard data is available")
    log_event(_LOGGER, "dashboard_state_rendered", outcome=result.visible_status)
    return result
