# Results

Only measurements produced by a verified command belong here. The table below records the
current verification state; pending values are intentionally not estimated.

| Check | Result | Command / evidence |
| --- | --- | --- |
| Documentation contract | Verified: 2 passed | `.venv/bin/python -m pytest tests/test_red_contracts.py -k 'tc_032 or tc_033' --maxfail=1` |
| CSV requirement mapping | Verified: 50 rows / 33 requirements | `.venv/bin/python scripts/validate_csv_mapping.py` |
| Branch coverage | Verified: 67 passed, 85.04% | `make PYTHON=.venv/bin/python coverage` |
| Compose configuration | Verified: valid | `docker compose config` |
| Compose test profile | Verified: 67 passed, 85.00% branch coverage | `docker compose --profile test run --rm tests` |
| ETL replay | Verified: 2 runs, 46 source facts, stable graph hash `fdd2cb4741fd102a7814012e7fe54804a77ae3d4eee1be51ae81d7807307edcf` | `docker compose --profile etl run --rm etl` twice; CRM 20, billing 14, support 12 |
| HTTP acceptance probes | Verified: dashboard/live/ready/v1 health/stats/ask/query routes; supported ask 200 with grounded evidence, unsupported ask 422, read-only SPARQL GET/POST 200, update 400 | Local Compose API probes against `127.0.0.1:8000` |
| CI basic validation | Verified: required Compose/ingest/test/coverage commands and no cloud credential references | `.github/workflows/ci.yml` structural validation |

Update this table only after running the named command in the target clean environment.
Do not convert a configured threshold into a measured result.
