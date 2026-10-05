# type-10052026-Maurice: Verify the six bounded catalog intents offline.
"""Executable contract tests for the ticket 08 query catalog."""

from kg.query.catalog import RDFLibGraphStore, all_intents, benchmark, execute


def test_seeded_catalog_results_and_timings() -> None:
    # type-10052026-Maurice: Check deterministic fixture counts and timing bounds.
    records = benchmark(RDFLibGraphStore())
    assert len(records) == 6
    assert all(record.error is None for record in records)
    assert all(record.result_count == record.expected_rows for record in records)
    assert all(record.elapsed_ms >= 0 for record in records)


def test_catalog_rejects_raw_and_unknown_requests_without_store_calls() -> None:
    # type-10052026-Maurice: Ensure unsafe input fails before the store seam.
    store = RDFLibGraphStore()
    for intent in ("SELECT * WHERE {?s ?p ?o}", "UPDATE", "unknown_intent"):
        result = execute(intent, {}, store=store)
        assert result.error is not None
        assert result.store_calls == 0
    assert store.calls == 0


def test_catalog_timeout_is_read_only() -> None:
    # type-10052026-Maurice: Keep timeout output stable and mutation-free.
    result = execute("unpaid_invoices", {}, force_timeout=True)
    assert result.error is not None and result.error.code == "query_timeout"
    assert result.mutated is False


def test_catalog_metadata_is_bounded() -> None:
    # type-10052026-Maurice: Keep the public catalog metadata machine-readable.
    assert len(all_intents()) == 6
    assert all(item.cap <= 1000 and item.timeout_seconds <= 5 and item.elapsed_ms >= 0 for item in all_intents())
