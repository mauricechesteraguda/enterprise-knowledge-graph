#!/usr/bin/env python3
# type-10052026-Maurice: Fail closed when the reviewable test mapping loses coverage.
"""Validate the committed requirement/test-case mapping without external services."""
import csv
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/test-cases/enterprise-kg-mvp.csv")
required = {f"REQ-{number:02d}" for number in range(1, 34)}
seen_requirements: set[str] = set()
seen_cases: set[str] = set()
rows = 0
with path.open(newline="", encoding="utf-8") as stream:
    reader = csv.DictReader(stream)
    required_columns = {"Test Case ID", "Requirement ID", "Automated Test Ref", "Expected Result"}
    missing_columns = sorted(required_columns - set(reader.fieldnames or []))
    if missing_columns:
        print(json.dumps({"event": "csv_mapping_failed", "error_code": "missing_columns", "columns": missing_columns}))
        raise SystemExit(1)
    for row in reader:
        rows += 1
        case = row["Test Case ID"]
        requirement = row["Requirement ID"]
        if not re.fullmatch(r"TC-\d{3}", case) or case in seen_cases:
            print(json.dumps({"event": "csv_mapping_failed", "error_code": "invalid_case_id", "case": case}))
            raise SystemExit(1)
        if requirement not in required:
            print(json.dumps({"event": "csv_mapping_failed", "error_code": "invalid_requirement", "case": case}))
            raise SystemExit(1)
        if not row["Expected Result"].strip() or not row["Automated Test Ref"].strip():
            print(json.dumps({"event": "csv_mapping_failed", "error_code": "incomplete_mapping", "case": case}))
            raise SystemExit(1)
        seen_cases.add(case)
        seen_requirements.add(requirement)
missing = sorted(required - seen_requirements)
if missing:
    print(json.dumps({"event": "csv_mapping_failed", "error_code": "unmapped_requirements", "requirements": missing}))
    raise SystemExit(1)
print(json.dumps({"event": "csv_mapping_validated", "rows": rows, "requirements": len(seen_requirements), "outcome": "success"}))
