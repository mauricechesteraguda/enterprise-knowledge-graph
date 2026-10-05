# type-10052026-Maurice: Isolate optional OpenAI-compatible HTTP provider behavior.
"""Small provider adapter; never logs request content or credentials."""
from __future__ import annotations

import json
from typing import Any, Callable, Sequence

from kg.observability.tracing import trace_call


class OpenAICompatibleGenerator:
    # type-10052026-Maurice: Depend on an injected transport so tests need no network.
    @trace_call
    def __init__(self, transport: Callable[..., Any], model: str, endpoint: str) -> None:
        self._transport = transport
        self.model = model[:100]
        self.endpoint = endpoint[:500]

    @trace_call
    def generate(self, context: Sequence[str], max_tokens: int = 512) -> str:
        # type-10052026-Maurice: Send only bounded context and parse one bounded response field.
        payload = {"model": self.model, "messages": [{"role": "user", "content": "\n".join(context)[:32000]}], "max_tokens": min(max_tokens, 2048)}
        response = self._transport(self.endpoint, json=payload)
        data = response if isinstance(response, dict) else json.loads(response)
        choices = data.get("choices", [])
        if not choices or not isinstance(choices[0], dict):
            raise RuntimeError("provider_invalid_response")
        message = choices[0].get("message", {})
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("provider_invalid_response")
        return text[: max(1, max_tokens * 4)]
