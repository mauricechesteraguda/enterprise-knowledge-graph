# type-10052026-Maurice: Extend existing CSV scenarios with public-seam error branches.
"""Behavior-focused branch coverage for already registered enterprise KG cases."""
from __future__ import annotations

import json
import logging
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_tc_003_uri_rejects_unsafe_identifiers() -> None:
    from kg.ontology.uris import canonical_uri, source_record_uri

    with pytest.raises(ValueError):
        canonical_uri("Person/Child", "safe")
    with pytest.raises(ValueError):
        canonical_uri("Person", "unsafe/id")
    with pytest.raises(ValueError):
        source_record_uri("crm/unsafe", "record")


def test_tc_008_query_safety_covers_validation_and_store_failure() -> None:
    from kg.query.catalog import execute

    for intent, parameters in (("unknown_intent", {}), ("high_priority_products_quarter", {"quarter_start": "bad", "quarter_end": "2026-04-01"}), ("unpaid_invoices", {"unexpected": "x"})):
        result = execute(intent, parameters)
        assert result.error is not None
    class BrokenStore:
        calls = 0
        def query(self, *args: object, **kwargs: object) -> object:
            self.calls += 1
            raise RuntimeError("adapter failure")
    result = execute("unpaid_invoices", {}, store=BrokenStore())
    assert result.error is not None and result.error.code == "query_failed"


def test_tc_012_auth_modes_cover_all_outcomes() -> None:
    from kg.api.auth import authorize, mode_result

    assert authorize(None, expected=None).status == "disabled_explicit"
    assert authorize(None, expected="secret").status == "unauthorized"
    assert authorize("secret", expected="secret").status == "authorized"
    assert authorize("wrong", expected="secret").status == "forbidden"
    assert mode_result(required=False, key=None).status == "disabled_explicit"
    assert mode_result(required=True, key=None).status == "unauthorized"
    assert mode_result(required=True, key="secret").status == "unauthorized"


def test_tc_014_logging_formatter_and_configuration_are_json_safe(caplog: pytest.LogCaptureFixture) -> None:
    from kg.observability.logging import JsonFormatter, configure_logging, get_logger, log_event, log_exception, serialize_event

    configure_logging()
    logger = get_logger("test-ticket13")
    with caplog.at_level(logging.INFO):
        log_event(logger, "safe_event", request_id="req-1", prompt="secret prompt", token="secret")
    record = logging.LogRecord("test-ticket13", logging.INFO, __file__, 1, "safe_event", (), None)
    record.event_fields = {"event": "safe_event", "request_id": "req-1", "prompt": "secret prompt", "token": "secret"}
    encoded = JsonFormatter().format(record)
    assert "secret prompt" not in encoded and "secret" not in encoded
    sanitized = serialize_event(intent="customer@example.test", source="https://secret.example/path", request_id="caller@example.test")
    assert "customer@example.test" not in sanitized and "https://secret.example/path" not in sanitized and "caller@example.test" not in sanitized
    secrets = serialize_event(event="token=REDACTED_VALUE", operation="authorization: Bearer REDACTED_VALUE", outcome="credential=REDACTED_VALUE")
    assert "REDACTED_VALUE" not in secrets and "graph_published" in serialize_event(event="graph_published")
    class Hostile:
        def __str__(self) -> str: raise AssertionError("must not stringify")
    class HostileKey:
        def __str__(self) -> str: raise AssertionError("must not stringify")
    cycle: list[object] = []
    cycle.append(cycle)
    nested = {HostileKey(): Hostile(), "token": "NESTED_REDACTED_VALUE", "email": "person@example.test", "cycle": cycle}
    normalized = json.loads(serialize_event(outcome=nested, elapsed_ms=float("nan"), request_id=float("inf")))
    assert "NESTED_REDACTED_VALUE" not in json.dumps(normalized) and "person@example.test" not in json.dumps(normalized)
    assert normalized["elapsed_ms"] == "NaN" and normalized["request_id"] == "Infinity"
    assert "<object>" in serialize_event(outcome=object())
    try:
        raise RuntimeError("private detail")
    except RuntimeError as exc:
        log_exception(logger, "safe_failure", exc, operation="test.operation", request_id="req-1")


def test_tc_016_health_optional_degradation_and_failure() -> None:
    from kg.operations.health import summarize

    assert summarize(fuseki="ok", crm="ok", pgvector="ok", provider="ok").status == "ok"
    assert summarize(fuseki="failed", crm="ok", pgvector="ok", provider="ok").required_failed is True
    assert summarize(fuseki="ok", crm="failed", pgvector="ok", provider="ok").required_failed is True
    assert summarize(fuseki="ok", crm="ok", pgvector="failed", provider="failed").status == "degraded"


def test_tc_017_and_tc_038_source_discovery_and_connector_errors(tmp_path: Path) -> None:
    from kg.config import Settings
    from kg.etl.sources import SourceSpec, connector_for, inspect, source_configs

    settings = Settings(fixture_dir=tmp_path, mappings_dir=tmp_path, billing_csv=tmp_path / "billing.csv", support_json=tmp_path / "support.json")
    assert len(source_configs(settings)) == 3
    assert inspect("empty", settings).status == "empty"
    assert inspect("partial", settings).status == "partial"
    assert inspect("malformed", settings).status == "failed"
    assert inspect("missing", settings).status == "failed"
    with pytest.raises(ValueError):
        connector_for(SourceSpec("x", "unknown", tmp_path / "x", tmp_path / "x"), settings)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"new": {"connector_type": "json", "path": "data.json", "mapping": "map.ttl"}}), encoding="utf-8")
    configured = settings.model_copy(update={"source_manifest": manifest})
    assert source_configs(configured)[0].name == "new"
    from kg.etl.cli import run as etl_run
    with pytest.raises(ValueError, match="invalid_run_id"):
        etl_run(run_id="../escape", artifact_dir=str(tmp_path))
    assert not (tmp_path / "escape").exists()


def test_tc_019_fixture_generation_and_validation(tmp_path: Path) -> None:
    from kg.fixtures import generate_fixtures, raw_hash

    paths = generate_fixtures(output_dir=tmp_path)
    assert set(paths) == {"crm", "billing", "support"}
    assert raw_hash({"b": 1, "a": 2}) == raw_hash({"a": 2, "b": 1})
    with pytest.raises(ValueError):
        generate_fixtures(data_as_of="not-a-date", output_dir=tmp_path / "bad")


def test_tc_023_query_routes_reject_methods_and_bound_inputs() -> None:
    from kg.api.query_routes import dispatch

    assert dispatch("PUT", intent="unpaid_invoices", parameters={}).error_code == "method_not_allowed"
    result = dispatch("GET", intent="unknown_intent", parameters={}, limit=5000, timeout_seconds=50)
    assert result.mutated is False and result.error_code is not None


def test_tc_027_and_tc_048_dashboard_states_are_explicit() -> None:
    from kg.dashboard.views import required_api_views, state

    assert len(required_api_views()) == 5
    assert {state(health=value).visible_status for value in ("loading", "pending", "503", "empty", "no_data", "unsupported", "ready")} == {"loading", "error", "empty", "unsupported", "ready"}


def test_tc_029_metrics_reject_unbounded_labels_and_record_errors() -> None:
    from kg.observability.metrics import record_stage

    record_stage("evidence", "degraded", 0.001)
    record_stage("evidence", "failed", 0.001, "test_error")
    with pytest.raises(ValueError):
        record_stage("customer-name", "success", 0.001)
    from kg.graphrag.retrieval import retrieve
    class BrokenVector:
        def search(self, *args: object) -> object:
            raise RuntimeError("private vector detail")
    result = retrieve("unpaid_invoices", {}, vector_store=BrokenVector())
    assert result.error_code is None and result.chunks == ()
    from kg.query.catalog import execute
    class ContextStore:
        def query(self, intent: str, parameters: dict[str, str], limit: int, timeout_seconds: int, *, request_id: str | None = None, run_id: str | None = None) -> list[dict[str, str]]:
            assert request_id == "req-029" and run_id == "run-029"
            return []
    assert execute("unpaid_invoices", {}, store=ContextStore(), request_id="req-029", run_id="run-029").error is None
    from kg.query.catalog import _query_store
    query_calls: list[dict[str, object]] = []
    class QueryNone:
        def query(self, *args: object) -> list[dict[str, str]]:
            query_calls.append({"args": args})
            return []
    class QueryRequest:
        def query(self, *args: object, request_id: str | None = None) -> list[dict[str, str]]:
            query_calls.append({"request_id": request_id})
            return []
    class QueryRun:
        def query(self, *args: object, run_id: str | None = None) -> list[dict[str, str]]:
            query_calls.append({"run_id": run_id})
            return []
    class QueryBoth:
        def query(self, *args: object, request_id: str | None = None, run_id: str | None = None) -> list[dict[str, str]]:
            query_calls.append({"request_id": request_id, "run_id": run_id})
            return []
    class QueryKwargs:
        def query(self, *args: object, **kwargs: object) -> list[dict[str, str]]:
            query_calls.append(kwargs)
            return []
    for adapter in (QueryNone(), QueryRequest(), QueryRun(), QueryBoth(), QueryKwargs()):
        _query_store(adapter, "unpaid_invoices", {}, 10, 1, request_id="req-029", run_id="run-029")
    assert query_calls == [{"args": ("unpaid_invoices", {}, 10, 1)}, {"request_id": "req-029"}, {"run_id": "run-029"}, {"request_id": "req-029", "run_id": "run-029"}, {"request_id": "req-029", "run_id": "run-029"}]
    from kg.graph.publication import _store_call
    calls: list[dict[str, object]] = []
    class NoContext:
        def op(self, value: str) -> None: calls.append({"value": value})
    class RequestOnly:
        def op(self, value: str, *, request_id: str | None = None) -> None: calls.append({"value": value, "request_id": request_id})
    class RunOnly:
        def op(self, value: str, *, run_id: str | None = None) -> None: calls.append({"value": value, "run_id": run_id})
    class Both:
        def op(self, value: str, *, request_id: str | None = None, run_id: str | None = None) -> None: calls.append({"value": value, "request_id": request_id, "run_id": run_id})
    class AnyContext:
        def op(self, value: str, **kwargs: object) -> None: calls.append({"value": value, **kwargs})
    for adapter in (NoContext(), RequestOnly(), RunOnly(), Both(), AnyContext()):
        _store_call(adapter, "op", "value", request_id="req-029", run_id="run-029")
    assert calls == [{"value": "value"}, {"value": "value", "request_id": "req-029"}, {"value": "value", "run_id": "run-029"}, {"value": "value", "request_id": "req-029", "run_id": "run-029"}, {"value": "value", "request_id": "req-029", "run_id": "run-029"}]
    from kg.graphrag.ask import answer
    class BrokenProvider:
        def generate(self, *args: object) -> str:
            raise RuntimeError("private provider detail")
    assert answer("approved question", facts=[{"subject": "s"}], provider=BrokenProvider()).provider_status == "failed"


def test_tc_030_performance_budget_measurement_and_ci_tolerance(monkeypatch: pytest.MonkeyPatch) -> None:
    from kg.operations.performance import Measurement, assert_budget, configured, measure

    budgets = configured()
    result, measurement = measure("unit", budgets.non_llm_api_seconds, lambda: "done")
    assert result == "done" and measurement.within_budget
    with pytest.raises(AssertionError):
        assert_budget(Measurement("slow", 2.0, 1.0))
    monkeypatch.setenv("CI", "1")
    assert Measurement("ci", 1.05, 1.0).within_budget


def test_tc_043_artifact_security_rejects_payload_and_permission_edges(tmp_path: Path) -> None:
    from kg.artifacts.security import validate_path, validate_payload, validate_permissions

    assert validate_path("safe/run.json", tmp_path).accepted
    for candidate in ("", "a//b", "%252e%252e/out", "/absolute", "C:/absolute", "a/../b", "a/%00"):
        assert not validate_path(candidate, tmp_path).accepted
    assert validate_payload({"x": "y"}, max_bytes=100).accepted
    assert validate_payload({"x": "y"}, max_bytes=1).error_code == "payload_too_large"
    assert validate_payload({}, max_bytes=0).error_code == "invalid_limit"
    assert validate_permissions(tmp_path / "missing.json")
    world = tmp_path / "world.json"
    world.write_text("{}", encoding="utf-8")
    world.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IWOTH)
    assert not validate_permissions(world)
    assert not validate_path("run/file.txt", tmp_path, run_id="../escape").accepted
    outside = tmp_path.parent / "tc043-outside"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    assert not validate_path("link/file.json", tmp_path).accepted
    from kg.etl.pipeline import _write_artifact
    import kg.etl.pipeline as pipeline
    original_write_json_artifact = pipeline.write_json_artifact
    pipeline.write_json_artifact = lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("payload_too_large"))
    try:
        with pytest.raises(ValueError, match="payload_too_large"):
            _write_artifact(tmp_path, "safe-run", "oversized.json", {"x": "y"})
    finally:
        pipeline.write_json_artifact = original_write_json_artifact
    assert not (tmp_path / "safe-run" / "oversized.json").exists()
    from kg.governance.validation import validate_and_quarantine
    report_path = tmp_path / "reports" / "validation.json"
    validate_and_quarantine({"type": "Invoice", "source_record_id": "invoice-1"}, "run-043", report_path, tmp_path)
    assert report_path.is_file()
    with pytest.raises(RuntimeError, match="persistence"):
        validate_and_quarantine({"type": "Invoice", "source_record_id": "invoice-1"}, "run-043", tmp_path.parent / "escape.json", tmp_path)
    from kg.query.catalog import write_benchmark_artifact
    benchmark_path = write_benchmark_artifact(tmp_path / "benchmark.json", artifact_root=tmp_path)
    assert benchmark_path.is_file()
    with pytest.raises(ValueError, match="escapes root"):
        write_benchmark_artifact(tmp_path.parent / "escape.json", artifact_root=tmp_path)
    from kg.graph.publication import SparqlGraphStoreHTTP
    requests: list[object] = []
    class Response:
        status = 200
        def __enter__(self) -> "Response": return self
        def __exit__(self, *args: object) -> None: return None
    def opener(request: object, timeout: int) -> Response:
        requests.append(request)
        return Response()
    SparqlGraphStoreHTTP("https://graph.example", opener=opener).put_graph("https://example.org/graph/safe", (), request_id="req-043", run_id="run-043")
    headers = dict(requests[0].header_items())  # type: ignore[attr-defined]
    assert headers["X-request-id"] == "req-043" and headers["X-run-id"] == "run-043"


def test_tc_044_api_error_and_request_correlation() -> None:
    from kg.api.app import create_app
    from kg.config import Settings

    class Store:
        calls = 0
        def health(self) -> bool:
            return True
        def sparql(self, query: str, *, limit: int, timeout_seconds: int) -> list[dict[str, str]]:
            self.calls += 1
            return [{"subject": "fixture"}]
        def query(self, intent: str, parameters: dict[str, str], limit: int, timeout_seconds: int) -> list[dict[str, str]]:
            self.calls += 1
            return [{"subject": "fixture"}]
        def list_entities(self, *, offset: int, limit: int) -> list[dict[str, str]]:
            return [{"id": "one"}]
        def system_stats(self) -> dict[str, int]:
            return {"entities": 1, "unsafe": "ignored"}  # type: ignore[dict-item]

    client = TestClient(create_app(settings=Settings(), graph_store=Store()))
    response = client.get("/health/live", headers={"X-Request-ID": "req-test"})
    assert response.status_code == 200 and response.headers["X-Request-ID"] == "req-test"
    assert client.get("/health/ready").status_code == 200
    assert client.get("/metrics").status_code == 200
    assert client.get("/v1/entities").json()["items"] == [{"id": "one"}]
    assert client.get("/v1/stats").json()["stats"] == {"entities": 1}
    assert client.get("/v1/query", params={"intent": "unpaid_invoices"}).status_code == 200
    assert client.get("/v1/sparql", params={"query": "SELECT * WHERE {?s ?p ?o}"}).status_code == 200
    assert client.get("/v1/sparql", params={"query": "UPDATE"}).status_code == 400
    bad = client.post("/v1/ask", json={"question": ""})
    assert bad.status_code == 422 and "request_id" in bad.json()["error"]
