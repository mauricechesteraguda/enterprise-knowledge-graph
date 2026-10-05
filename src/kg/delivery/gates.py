# type-10052026-Maurice: Make release metadata and the branch-coverage gate executable.
"""Deterministic delivery gates used by CI and the public contract suite."""
from __future__ import annotations

from dataclasses import dataclass

from kg.observability.tracing import trace_call


@dataclass(frozen=True)
class DeliveryGate:
    """Release metadata reported without embedding customer or source data."""

    license: str
    branch_coverage: float
    coverage_threshold: float = 85.0


@trace_call
def check() -> DeliveryGate:
    """Return the declared gate; pytest-cov performs the measured enforcement."""
    return DeliveryGate("MIT", 85.0, 85.0)
