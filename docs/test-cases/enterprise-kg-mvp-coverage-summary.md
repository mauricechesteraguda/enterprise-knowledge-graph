# Enterprise KG MVP test-case coverage summary

This is the reviewable use-case specification for ticket 02 plus ticket 03's deterministic RED mapping. Cases remain unexecuted (`Not Run`) until the corresponding behavior is implemented. Team 1 scope: no subagents were spawned (no reviewer/debugger subagents).

## Deterministic inventory

- CSV: `docs/test-cases/enterprise-kg-mvp.csv`
- Test cases: 50 (`TC-001` through `TC-050`, sequential and never reused)
- Requirement IDs: `REQ-01` through `REQ-33`
- Required outcome fields: `Expected Result` populated; `Actual Result` and `Remarks / Defects ID` blank; `Status (Pass/Fail)` exactly `Not Run`
- Sort order: ascending test-case ID
- Validator: external only at `/private/var/folders/hp/x3wtpd4n3r5_9x42nvhscznc0000gq/T/opencode/agent-scripts/knowledge-graph/validate_enterprise_kg_csv.py`
- RED mapping validator: `/private/var/folders/hp/x3wtpd4n3r5_9x42nvhscznc0000gq/T/opencode/validate_red_contract_mapping.py`; result `50/50` CSV cases mapped to matching RED test IDs.

### Exact scripted Test Type counts

| Test Type | Cases |
|---|---:|
| Boundary | 5 |
| Integration | 12 |
| Negative | 10 |
| Permission | 3 |
| Positive | 4 |
| Regression | 8 |
| Security | 8 |
| **Total** | **50** |

Open Questions: None; confirmed design decisions resolve ambiguities.

## Requirement coverage

Every requirement has at least one concrete case. Additional cases cover failure, boundary, security, replay, concurrency-adjacent atomicity, partial failure, timeout, bad payload, no-results, provider outage, loading, and degraded-mode behavior.

| Requirement range | Covered by |
|---|---|
| REQ-01 | TC-001, TC-050 |
| REQ-02 | TC-002 |
| REQ-03 | TC-003 |
| REQ-04 | TC-004, TC-034, TC-035 |
| REQ-05 | TC-005, TC-018, TC-042, TC-045 |
| REQ-06 | TC-006 |
| REQ-07 | TC-007, TC-036, TC-037 |
| REQ-08 | TC-008 |
| REQ-09 | TC-009, TC-041 |
| REQ-10 | TC-010 |
| REQ-11 | TC-011, TC-040 |
| REQ-12 | TC-012 |
| REQ-13 | TC-013, TC-043, TC-044 |
| REQ-14 | TC-014 |
| REQ-15 | TC-015 |
| REQ-16 | TC-016, TC-046, TC-049 |
| REQ-17 | TC-017, TC-038 |
| REQ-18 | TC-018 |
| REQ-19 | TC-019 |
| REQ-20 | TC-020 |
| REQ-21 | TC-021 |
| REQ-22 | TC-022 |
| REQ-23 | TC-023, TC-039 |
| REQ-24 | TC-024, TC-047 |
| REQ-25 | TC-025 |
| REQ-26 | TC-026 |
| REQ-27 | TC-027, TC-048 |
| REQ-28 | TC-028 |
| REQ-29 | TC-029 |
| REQ-30 | TC-030 |
| REQ-31 | TC-031 |
| REQ-32 | TC-032 |
| REQ-33 | TC-033 |

## Checklist categories

All 14 categories are applicable and represented. N/A reasons: None; every checklist category has concrete coverage.

| Category | Representative cases |
|---|---|
| Foundation / reproducibility | TC-001, TC-050 |
| Ontology / URI / provenance | TC-002, TC-003 |
| Fixtures / connectors / executable RML | TC-019, TC-038, TC-046 |
| SHACL governance / quarantine | TC-004, TC-020, TC-034, TC-035 |
| ETL lifecycle / artifacts | TC-005, TC-017, TC-018, TC-042 |
| Identity resolution | TC-006, TC-007, TC-021, TC-036, TC-037 |
| Graph publication / atomicity | TC-005, TC-045 |
| Query catalog / SPARQL safety | TC-008, TC-022, TC-023, TC-039 |
| GraphRAG / LLM / grounding | TC-009, TC-011, TC-025, TC-040, TC-041 |
| Evidence / auditability | TC-010, TC-024, TC-026, TC-047 |
| API contracts / authentication | TC-012, TC-013, TC-023, TC-028, TC-044 |
| Dashboard / loading / degraded UI | TC-027, TC-048 |
| Security / redaction / filesystem | TC-014, TC-043 |
| Observability / performance / CI / documentation / licensing | TC-015, TC-029, TC-030, TC-031, TC-032, TC-033 |

## Test-type intent

The inventory includes positive and regression cases for happy paths, negative cases for invalid and unsafe behavior, boundary cases for thresholds and limits, permission cases for API keys and read-only access, and integration cases for Compose/adapters/ETL/API. It also explicitly covers security, partial failure, timeouts, bad payloads, no results, provider failures, atomicity and loading states.
