# Results

Only measurements produced by a verified command belong here. The table below records the
current verification state; pending values are intentionally not estimated.

| Check | Result | Command / evidence |
| --- | --- | --- |
| Documentation contract | Verified: 2 passed | `.venv/bin/python -m pytest tests/test_red_contracts.py -k 'tc_032 or tc_033' --maxfail=1` |
| CSV requirement mapping | Verified: 50 rows / 33 requirements | `.venv/bin/python scripts/validate_csv_mapping.py` |
| Branch coverage | Verified: 67 passed, 85.10% | `make coverage` |
| Compose configuration | Verified: valid | `docker compose config` |

Update this table only after running the named command in the target clean environment.
Do not convert a configured threshold into a measured result.
