# Integration guide

## Add a supported source instance

1. Add a fixture or local seed under `data/` with a stable `source_id` per record.
2. Implement `SourceConnector.extract(run_id)` (or configure an existing connector) and
   return `SourceRecord` values through `validate_connector_record`.
3. Add an RML mapping under `mappings/`, ontology terms under `ontology/`, and SHACL rules
   under `shapes/` when the source introduces new predicates.
4. Register the source in the ETL orchestration and add a deterministic replay test.
5. Confirm the manifest, provenance fields, quarantine report, and named-graph replacement.

## Add a protocol

Implement an adapter behind the smallest existing protocol in `src/kg/ports.py`. Keep
credentials and transport details inside the adapter. Adapters must enforce bounded reads,
timeouts, and redaction; they must not expand the query catalog or bypass publication gates.
Use dependency injection in tests so the baseline remains offline.

## External SPARQL

An external endpoint may implement `GraphStore`, but it is not a requirement of this
repository. Configure it outside committed files, use a read-only account, enforce the same
five-second/1,000-row caps, and preserve the catalog allowlist. Do not pass caller-supplied
SPARQL to the API proxy. Test health failure and timeout behavior before enabling it.

## Calling the API

Start the local service with `make up`, then use `GET /health/live` without credentials.
Protected endpoints require `X-API-Key` only when `KG_API_KEY` is configured. The supported
interfaces are `GET /v1/query?intent=...`, `GET|POST /v1/sparql` for safe read-only queries,
and `POST /v1/ask` for bounded GraphRAG. See `docs/query-catalog.md` for intents and limits.
