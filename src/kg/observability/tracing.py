# type-10052026-Maurice: Keep development tracing external and session-scoped.
"""External, session-scoped function tracing with bounded metadata."""
from __future__ import annotations
import functools
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, ParamSpec, TypeVar, cast
P = ParamSpec("P")
R = TypeVar("R")
_REPO_HASH = hashlib.sha256(str(Path.cwd().resolve()).encode("utf-8")).hexdigest()[:16]
_SESSION_ID = re.sub(r"[^A-Za-z0-9_.-]", "_", os.environ.get("OPENCODE_SESSION_ID", os.environ.get("SESSION_ID", "local")))[:80]
_TRACE_PATH = Path.home() / ".cache" / "agent-trace" / _REPO_HASH / _SESSION_ID / "foundation.jsonl"
def _write_trace(event: dict[str, Any]) -> None:
    """Write bounded metadata outside the repository."""
    _TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _TRACE_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")
def trace_call(func: Callable[P, R]) -> Callable[P, R]:
    """Trace entry, successful exit, and exception without argument values."""
    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        name = f"{func.__module__}.{func.__qualname__}"
        _write_trace({"ts": datetime.now(timezone.utc).isoformat(), "phase": "entry", "function": name})
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            _write_trace({"ts": datetime.now(timezone.utc).isoformat(), "phase": "exception", "function": name, "error_type": type(exc).__name__})
            raise
        _write_trace({"ts": datetime.now(timezone.utc).isoformat(), "phase": "exit", "function": name, "outcome": "success"})
        return result
    return cast(Callable[P, R], wrapped)
@trace_call
def trace_path() -> Path:
    """Return the external trace path for operational validation."""
    return _TRACE_PATH
