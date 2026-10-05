# type-10052026-Maurice: Expose deterministic fixture generation as a local CLI.
"""Generate committed-compatible synthetic source fixtures."""
from __future__ import annotations

import argparse

from kg.fixtures import generate_fixtures
from kg.observability.tracing import trace_call


@trace_call
def main() -> None:
    # type-10052026-Maurice: Parse only deterministic generation options.
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data-as-of", default="2026-01-31")
    parser.add_argument("--output-dir", default="data/raw")
    args = parser.parse_args()
    generate_fixtures(args.seed, args.data_as_of, args.output_dir)


if __name__ == "__main__":
    main()
