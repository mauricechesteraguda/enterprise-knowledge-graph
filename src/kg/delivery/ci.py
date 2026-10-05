# type-10052026-Maurice: Keep local and CI delivery commands machine-readable.
"""CI command contract for the reproducible Compose test path."""
from dataclasses import dataclass

from kg.observability.tracing import trace_call


@dataclass(frozen=True)
class WorkflowContract:
    commands: frozenset[str]


@trace_call
def workflow_contract() -> WorkflowContract:
    return WorkflowContract(frozenset({"compose", "ingest", "test", "coverage"}))
