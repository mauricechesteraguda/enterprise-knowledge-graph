.PHONY: install lint format typecheck test check
install:
	python -m pip install -e '.[dev]'
lint:
	python -m ruff check src
format:
	python -m ruff format src
typecheck:
	python -m mypy src
test:
	python -m pytest
check: lint typecheck
