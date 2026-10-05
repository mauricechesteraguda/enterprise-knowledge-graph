# type-10052026-Maurice: Reject traversal and unsafe artifact destinations before I/O.
"""Safe artifact path resolution confined to the configured artifact root."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote
from typing import Any

from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

_LOGGER = get_logger(__name__)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_DEFAULT_MAX_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class PathValidation:
    # type-10052026-Maurice: Return safe metadata without echoing untrusted path values.
    accepted: bool
    path: Path | None = None
    error_code: str | None = None
    message: str = ""


@dataclass(frozen=True)
class PayloadValidation:
    # type-10052026-Maurice: Make artifact payload limits explicit and machine-readable.
    accepted: bool
    size_bytes: int
    error_code: str | None = None
    message: str = ""


@trace_call
def write_json_artifact(root: str | Path, name: str, payload: Any, *, max_bytes: int = _DEFAULT_MAX_BYTES) -> Path:
    # type-10062026-Maurice: Centralize confined, permission-aware, size-checked JSON persistence.
    checked = validate_path(name, root)
    if not checked.accepted or checked.path is None or not validate_permissions(checked.path):
        raise ValueError(checked.error_code or "invalid_artifact_path")
    try:
        serialized = json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n"
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("artifact_serialization_failed") from exc
    validation = validate_payload(serialized, max_bytes=max_bytes)
    if not validation.accepted:
        raise ValueError(validation.error_code or "artifact_payload_rejected")
    checked.path.parent.mkdir(parents=True, exist_ok=True)
    checked.path.write_text(serialized, encoding="utf-8")
    return checked.path


@trace_call
def _reject(code: str, message: str) -> PathValidation:
    # type-10052026-Maurice: Log only a bounded error code, never paths or payloads.
    log_event(_LOGGER, "artifact_security_rejected", outcome="failed", error_code=code)
    return PathValidation(False, error_code=code, message=message)


@trace_call
def _decoded_candidate(candidate: str) -> str | None:
    # type-10052026-Maurice: Decode bounded URL encoding before checking traversal markers.
    value = candidate
    for _ in range(3):
        decoded = unquote(value)
        if decoded == value:
            break
        value = decoded
    if "%" in value or "\x00" in value:
        return None
    return value


@trace_call
def _valid_identifier(value: str) -> bool:
    # type-10052026-Maurice: Permit only stable run/source identifiers used by artifact partitions.
    return bool(_IDENTIFIER.fullmatch(value)) and value not in {".", ".."}


@trace_call
def validate_path(candidate: str, artifact_root: str | Path = "artifacts", *, run_id: str | None = None, source: str | None = None) -> PathValidation:
    # type-10052026-Maurice: Resolve paths strictly under the configured root, including symlinks.
    if not isinstance(candidate, str) or not candidate or len(candidate) > 1024:
        return _reject("invalid_path", "artifact path rejected")
    decoded = _decoded_candidate(candidate)
    if decoded is None or "\x00" in decoded:
        return _reject("invalid_path", "artifact path rejected")
    path_text = decoded.replace("\\", "/")
    parts = path_text.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return _reject("path_traversal", "artifact path rejected")
    if Path(path_text).is_absolute() or re.match(r"^[A-Za-z]:/", path_text):
        return _reject("absolute_path", "artifact path rejected")
    if run_id is not None and (not isinstance(run_id, str) or not _valid_identifier(run_id)):
        return _reject("invalid_run_id", "artifact identity rejected")
    if source is not None and (not isinstance(source, str) or not _valid_identifier(source)):
        return _reject("invalid_source", "artifact identity rejected")
    if any(not _valid_identifier(part) for part in parts):
        return _reject("invalid_identifier", "artifact identity rejected")
    root = Path(artifact_root).expanduser().resolve(strict=False)
    resolved = (root / Path(*parts)).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        return _reject("path_escape", "artifact path rejected")
    if resolved.exists() and not os.access(resolved, os.R_OK):
        return _reject("permission_denied", "artifact access rejected")
    log_event(_LOGGER, "artifact_security_accepted", outcome="success")
    return PathValidation(True, path=resolved)


@trace_call
def validate_payload(payload: Any, *, max_bytes: int = _DEFAULT_MAX_BYTES) -> PayloadValidation:
    # type-10052026-Maurice: Bound serialized artifact payloads before persistence.
    if not isinstance(max_bytes, int) or max_bytes < 1:
        return PayloadValidation(False, 0, "invalid_limit", "artifact payload rejected")
    try:
        size = len(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError, OverflowError):
        return PayloadValidation(False, 0, "invalid_payload", "artifact payload rejected")
    if size > max_bytes:
        return PayloadValidation(False, size, "payload_too_large", "artifact payload rejected")
    return PayloadValidation(True, size)


@trace_call
def validate_permissions(path: str | Path) -> bool:
    # type-10052026-Maurice: Refuse world-writable artifact files when they already exist.
    target = Path(path)
    try:
        return not target.exists() or (target.stat().st_mode & 0o002) == 0
    except OSError:
        return False
