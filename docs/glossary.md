# Glossary

| Term | Meaning |
| --- | --- |
| Canonical resource | Stable `https://example.org/kg/{class}/{id}` entity assembled from sources. |
| Source record | Immutable source identity retained separately from canonical resources. |
| Provenance | Source system, record ID, run ID, hash, and fixed `data_as_of` metadata. |
| Named graph | Source-scoped graph replaced atomically during publication. |
| Quarantine | Machine-readable holding area for records failing SHACL or mapping gates. |
| Evidence snapshot | Immutable bounded retrieval metadata supporting a generated answer. |
| Grounding status | Whether an answer is supported by the available evidence and graph. |
| Query catalog | Read-only allowlist of named SPARQL intents and validated parameters. |
| Replay | Re-running a source with the same committed inputs and deterministic configuration. |
