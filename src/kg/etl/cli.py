# type-10052026-Maurice: Provide the intentionally narrow kg-etl run command.
"""Command-line orchestration for offline and GraphStore-backed ETL runs."""
from __future__ import annotations

import argparse
from types import SimpleNamespace
from kg.etl.pipeline import run as run_pipeline
from kg.observability.tracing import trace_call


@trace_call
def run(source: str = "all", run_id: str = "run-cli", data_as_of: str = "2026-01-31", artifact_dir: str = "artifacts") -> SimpleNamespace:
    """Library-friendly equivalent of the CLI command."""
    result = run_pipeline(source=source, run_id=run_id, data_as_of=data_as_of, artifact_dir=artifact_dir)
    return SimpleNamespace(status=result["status"], artifacts=result["artifacts"], run_id=run_id, data_as_of=data_as_of)


@trace_call
def main() -> None:
    """Parse ``kg-etl run [--source]`` and emit a JSON-safe summary."""
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
        print(json.dumps(run_pipeline(source=args.source, run_id=args.run_id, data_as_of=args.data_as_of, artifact_dir=args.artifact_dir), default=str, sort_keys=True))


if __name__ == "__main__":
    main()
