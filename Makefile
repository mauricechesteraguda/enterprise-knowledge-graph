.PHONY: install lint format typecheck package-completeness test coverage check compose-config build up etl compose-tests docs
PYTHON ?= python3
install:
	$(PYTHON) -m pip install -e '.[dev]'
lint:
	$(PYTHON) -m ruff check src
format:
	$(PYTHON) -m ruff format src
typecheck:
	$(PYTHON) -m mypy src
package-completeness:
	@test -f src/kg/artifacts/__init__.py && test -f src/kg/artifacts/security.py
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git ls-files --error-unmatch src/kg/artifacts/__init__.py src/kg/artifacts/security.py >/dev/null; fi
test:
	$(PYTHON) -m pytest
coverage:
	$(PYTHON) -m pytest --cov=src/kg --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=85 --maxfail=1
check: package-completeness lint typecheck

compose-config:
	docker compose config
build:
	docker compose build
up:
	docker compose up --build
etl:
	docker compose --profile etl run --rm etl
compose-tests:
	docker compose --profile test run --rm tests
docs:
	$(PYTHON) scripts/validate_csv_mapping.py
	$(PYTHON) -m pytest tests/test_red_contracts.py -k 'tc_032 or tc_033' --maxfail=1
