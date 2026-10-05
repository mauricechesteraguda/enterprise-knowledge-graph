# type-10052026-Maurice: Provide deterministic generation without credentials.
"""Offline generator used as the safe default and test fake."""
from __future__ import annotations

import hashlib
from typing import Sequence

from kg.observability.tracing import trace_call


@trace_call
def generate(context: str | Sequence[str], max_tokens: int = 512) -> str:
    # type-10052026-Maurice: Produce stable, evidence-shaped output without inventing facts.
    text = "\n".join(context) if not isinstance(context, str) else context
    bounded = text[: max(1, max_tokens * 4)]
    if not bounded.strip():
        return "No matching facts were retrieved."
    digest = hashlib.sha256(bounded.encode("utf-8")).hexdigest()[:12]
    return f"Retrieved facts ({digest}): {bounded}"
