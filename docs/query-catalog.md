# Bounded SPARQL query catalog

The catalog is a read-only allowlist in `kg.query.catalog`. It executes six
SPARQL 1.1 files through the `GraphStore.query` seam, never accepts caller
SPARQL, and caps each request at 1,000 rows and five seconds. Parameters are
validated ISO dates and are passed as RDF literal bindings; unknown intents,
updates, federation, path expressions, and unexpected parameters fail closed.

| Intent | Parameters | Seed rows |
| --- | --- | ---: |
| `cross_silo_unpaid_open_high` | none | 1 |
| `canonical_identity_records` | none | 1 |
| `unpaid_invoices_by_organization` | none | 1 |
| `high_priority_products_quarter` | `quarter_start`, `quarter_end` | 1 |
| `person_account_invoice_product_ticket` | none | 1 |
| `orphan_tickets` | none | 1 |

`benchmark(store)` returns machine-readable timing records with intent,
result count, expected count, cap, timeout, and monotonic `elapsed_ms`.
`write_benchmark_artifact(path)` writes the same stable JSON shape for offline
validation. The default `RDFLibGraphStore` is deterministic and is used when a
live Fuseki adapter is unavailable.
