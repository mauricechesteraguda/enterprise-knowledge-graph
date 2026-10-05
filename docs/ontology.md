# Ontology and governance

The modular Turtle vocabulary lives in `ontology/`: `core.ttl` defines the eight
classes, `billing.ttl` and `support.ttl` add source-specific terms, and
`taxonomy.ttl` defines SKOS status and priority concepts. Canonical resources use
`https://example.org/kg/{class}/{id}`; source records use a separate
`SourceRecord/{source}/{id}` path and are never canonical persons.

Every source-derived record carries `source_system`, `source_record`, `provenance`,
`run_id`, and fixed `data_as_of` metadata. `shapes/shapes.ttl` is the publication
gate. Failed records are retained in machine-readable quarantine reports with
shape, focus node, path, message, source record, and run ID. Runtime or report
persistence errors fail closed.
