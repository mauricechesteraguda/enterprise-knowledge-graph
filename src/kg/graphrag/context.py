# type-10052026-Maurice: Keep model context bounded and tool-free.
"""Deterministic context assembly for retrieved evidence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from kg.observability.tracing import trace_call


@dataclass(frozen=True)
class Context:
    # type-10052026-Maurice: Return only bounded text and token accounting.
    items: tuple[str, ...]
    token_count: int
    tools: tuple[str, ...] = ()


@trace_call
def assemble(items: Sequence[str], max_tokens: int = 8000, max_items: int = 50) -> Context:
    # type-10052026-Maurice: Cap each context item before adding it to the model input.
    if max_tokens < 1 or max_items < 1:
        raise ValueError("invalid_context_bound")
    output: list[str] = []
    used = 0
    for item in items[:max_items]:
        text = str(item)[:4000]
        tokens = max(1, (len(text) + 3) // 4)
        if used + tokens > max_tokens:
            break
        output.append(text)
        used += tokens
    return Context(tuple(output), used)
