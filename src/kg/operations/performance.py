# type-10052026-Maurice: Centralize measurable ticket-13 performance budgets.
"""Performance budget assertions for ETL, SPARQL, and non-LLM API paths."""
from __future__ import annotations

import os
from dataclasses import dataclass
from time import perf_counter
from typing import Callable, TypeVar

from kg.observability.tracing import trace_call

T = TypeVar("T")
ETL_SECONDS = 90.0
SPARQL_SECONDS = 2.0
NON_LLM_API_SECONDS = 1.0


@dataclass(frozen=True)
class PerformanceBudgets:
    etl_seconds: float = ETL_SECONDS
    sparql_seconds: float = SPARQL_SECONDS
    non_llm_api_seconds: float = NON_LLM_API_SECONDS


@dataclass(frozen=True)
class Measurement:
    operation: str
    elapsed_seconds: float
    budget_seconds: float

    @property
    def within_budget(self) -> bool:
        # type-10052026-Maurice: Permit only a documented CI measurement tolerance.
        tolerance = 1.10 if os.environ.get("CI") else 1.0
        return self.elapsed_seconds <= self.budget_seconds * tolerance


@trace_call
def configured() -> PerformanceBudgets:
    return PerformanceBudgets()


@trace_call
def measure(operation: str, budget_seconds: float, function: Callable[[], T]) -> tuple[T, Measurement]:
    started = perf_counter()
    result = function()
    return result, Measurement(operation, perf_counter() - started, budget_seconds)


@trace_call
def assert_budget(measurement: Measurement) -> Measurement:
    if not measurement.within_budget:
        raise AssertionError(
            f"{measurement.operation} exceeded {measurement.budget_seconds:.3f}s "
            f"with {measurement.elapsed_seconds:.3f}s"
        )
    return measurement
