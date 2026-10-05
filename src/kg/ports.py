# type-10052026-Maurice: Define stable adapter ownership boundaries only.
"""Typed boundaries for adapters introduced by later feature tickets."""
from dataclasses import dataclass
import inspect
from collections.abc import Mapping
from typing import Any, Protocol, Sequence
from kg.observability.tracing import trace_call
@dataclass(frozen=True)
class SourceRecord:
    """Minimal source identity boundary; raw values stay inside adapters."""
    source_system: str
    source_record_id: str
    run_id: str
    raw_hash: str = ""
    data_as_of: str = ""
    source_type: str = ""
    payload: dict[str, Any] | None = None
class SourceConnector(Protocol):
    """Extract bounded source records without storage coupling."""
    def extract(self, run_id: str) -> Sequence[SourceRecord]: ...

    # type-10052026-Maurice: Keep connector implementations interchangeable.
class GraphStore(Protocol):
    """Read/write graph boundary; Fuseki code belongs in an adapter."""
    def query(self, intent: str, parameters: dict[str, str], limit: int, timeout_seconds: int, *, request_id: str | None = None, run_id: str | None = None) -> Sequence[dict[str, str]]: ...

    # type-10052026-Maurice: Keep staged publication independent of any store vendor.
    def put_graph(self, graph_uri: str, triples: Sequence[tuple[str, str, str]]) -> None: ...
    def promote_graph(self, staging_uri: str, target_uri: str) -> None: ...
    def discard_graph(self, graph_uri: str) -> None: ...
class LLMPort(Protocol):
    """Bounded generation boundary with no retrieval or policy access."""
    def generate(self, context: Sequence[str], max_tokens: int) -> str: ...


class VectorStore(Protocol):
    """Bounded support-text retrieval boundary; implementations are adapters."""

    def search(self, query: str, limit: int, timeout_seconds: int) -> Sequence[dict[str, Any]]: ...


@trace_call
def call_with_optional_context(callable_object: Any, *args: Any, request_id: str | None = None, run_id: str | None = None) -> Any:
    # type-10062026-Maurice: Forward independently supported correlation keywords without breaking adapters.
    try:
        parameters: Mapping[str, inspect.Parameter] = inspect.signature(callable_object).parameters
    except (TypeError, ValueError):
        parameters = {}
    accepts_kwargs = any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values())
    context = {
        name: value
        for name, value in (("request_id", request_id), ("run_id", run_id))
        if accepts_kwargs or (name in parameters and parameters[name].kind in {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY})
    }
    return callable_object(*args, **context)
@trace_call
def validate_connector_record(record: SourceRecord) -> SourceRecord:
    """Validate stable IDs at the adapter boundary."""
    if not record.source_system or not record.source_record_id or not record.run_id:
        raise ValueError("source record identity is incomplete")
    return record
