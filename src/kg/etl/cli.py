# type-10052026-Maurice: Provide the intentionally narrow kg-etl run command.
"""Command-line orchestration for offline and GraphStore-backed ETL runs."""
from __future__ import annotations

import argparse
from types import SimpleNamespace
from kg.etl.pipeline import run as run_pipeline
from kg.observability.tracing import trace_call
from kg.observability.logging import configure_logging, get_logger, log_event, log_exception
from kg.artifacts.security import validate_path

_LOGGER = get_logger(__name__)


@trace_call
def run(source: str = "all", run_id: str = "run-cli", data_as_of: str = "2026-01-31", artifact_dir: str = "artifacts") -> SimpleNamespace:
    """Library-friendly equivalent of the CLI command."""
    # type-10062026-Maurice: Reject unsafe CLI identity before pipeline work.
    if not validate_path(f"{run_id}/manifest.json", artifact_dir, run_id=run_id).accepted:
        raise ValueError("invalid_run_id")
    log_event(_LOGGER, "etl_cli_started", run_id=run_id, source=source, outcome="started")
    result = run_pipeline(source=source, run_id=run_id, data_as_of=data_as_of, artifact_dir=artifact_dir)
    log_event(_LOGGER, "etl_cli_completed", run_id=run_id, source=source, outcome=result["status"])
    return SimpleNamespace(status=result["status"], artifacts=result["artifacts"], run_id=run_id, data_as_of=data_as_of)


@trace_call
def main() -> None:
    """Parse ``kg-etl run [--source]`` and emit a JSON-safe summary."""
    # type-10062026-Maurice: Configure structured logging before argument parsing or startup work.
    configure_logging()
    parser = argparse.ArgumentParser(prog="kg-etl")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("run")
    command.add_argument("--source", default="all", choices=("all", "crm", "billing", "support"))
    command.add_argument("--run-id", default="run-cli")
    command.add_argument("--data-as-of", default="2026-01-31")
    command.add_argument("--artifact-dir", default="artifacts")
    args = parser.parse_args()
    if args.command == "run":
        import json
        try:
            print(json.dumps(run(source=args.source, run_id=args.run_id, data_as_of=args.data_as_of, artifact_dir=args.artifact_dir).__dict__, default=str, sort_keys=True))
        except Exception as exc:
            log_exception(_LOGGER, "etl_cli_failed", exc, operation="etl.cli.run", run_id=args.run_id, error_code="etl_cli_failed")
            parser.error("ETL run rejected")


if __name__ == "__main__":
    main()
