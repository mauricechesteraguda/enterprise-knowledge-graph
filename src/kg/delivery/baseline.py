# type-10052026-Maurice: Publish the offline, credential-free baseline contract.
"""Machine-readable publication constraints for TC-033."""
from dataclasses import dataclass

from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

_LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class Baseline:
    """Facts a clean checkout can satisfy without external services."""

    license: str
    requires_cloud: bool
    requires_secret: bool


@trace_call
def inspect() -> Baseline:
    """Return the checked-in baseline policy without reading environment secrets."""
    result = Baseline("MIT", False, False)
    log_event(_LOGGER, "baseline_inspected", outcome="success")
    return result
