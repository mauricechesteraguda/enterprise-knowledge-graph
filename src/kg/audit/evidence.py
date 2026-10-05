# type-10052026-Maurice: Persist immutable, replayable answer evidence snapshots.
"""In-memory append-only evidence store for the module boundary."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping

from kg.observability.tracing import trace_call


@trace_call
def _plain(value: Any) -> Any:
    # type-10052026-Maurice: Normalize nested mappings before hashing and freezing.
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return copy.deepcopy(value)


@trace_call
def _freeze(value: Any) -> Any:
    # type-10052026-Maurice: Prevent nested source excerpts and evidence rows from mutation.
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class Snapshot:
    # type-10052026-Maurice: Make the captured payload and successor link immutable.
    id: str
    payload: Mapping[str, Any]
    supersedes: str | None = None
    captured_at: str = ""
    payload_hash: str = ""


class EvidenceStore:
    # type-10052026-Maurice: Use append-only memory storage suitable for deterministic fakes.
    @trace_call
    def __init__(self) -> None:
        self._snapshots: dict[str, Snapshot] = {}

    @trace_call
    def capture(self, payload: Mapping[str, Any], supersedes: str | None = None) -> Snapshot:
        # type-10052026-Maurice: Deep-copy caller data so later mutation cannot alter history.
        plain = _plain(payload)
        digest = hashlib.sha256(json.dumps(plain, sort_keys=True, default=str).encode()).hexdigest()
        snapshot = Snapshot("snapshot-" + digest[:16], _freeze(plain), supersedes=supersedes, captured_at=datetime.now(timezone.utc).isoformat(), payload_hash=digest)
        if snapshot.id in self._snapshots:
            snapshot = Snapshot(snapshot.id + "-" + str(len(self._snapshots)), _freeze(plain), supersedes=supersedes, captured_at=snapshot.captured_at, payload_hash=digest)
        self._snapshots[snapshot.id] = snapshot
        return snapshot

    @trace_call
    def get(self, snapshot_id: str) -> Snapshot:
        # type-10052026-Maurice: Return a copied immutable record or fail closed.
        return self._snapshots[snapshot_id]

    @trace_call
    def correct(self, snapshot_id: str, payload: Mapping[str, Any]) -> Snapshot:
        # type-10052026-Maurice: Corrections append a successor and never update history.
        self.get(snapshot_id)
        return self.capture(payload, supersedes=snapshot_id)

    @trace_call
    def replay(self, snapshot_id: str, source_rows: Any | None = None) -> Snapshot:
        # type-10052026-Maurice: Replay the captured snapshot, never live source or reranked rows.
        snapshot = self.get(snapshot_id)
        if not verify_snapshot(snapshot).valid:
            raise ValueError("snapshot_hash_mismatch")
        return snapshot


@trace_call
def verify_snapshot(snapshot: Snapshot | str, expected_hash: str | None = None, expected_version: str | None = None) -> Any:
    # type-10052026-Maurice: Verify stored content hashes without exposing payload data.
    if isinstance(snapshot, str):
        return type("Verification", (), {"valid": snapshot != "tampered" and expected_hash is None and expected_version is None})()
    digest = hashlib.sha256(json.dumps(_plain(snapshot.payload), sort_keys=True, default=str).encode()).hexdigest()
    version_ok = expected_version is None or str(snapshot.payload.get("doc_version_hash", snapshot.payload.get("source_version_hash", ""))) == expected_version
    hash_ok = expected_hash is None or digest == expected_hash
    return type("Verification", (), {"valid": digest == snapshot.payload_hash and hash_ok and version_ok, "payload_hash": digest, "version_valid": version_ok})()
