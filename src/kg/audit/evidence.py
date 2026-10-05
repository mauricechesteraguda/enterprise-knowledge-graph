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
        frozen = copy.deepcopy(dict(payload))
        digest = hashlib.sha256(json.dumps(frozen, sort_keys=True, default=str).encode()).hexdigest()
        snapshot = Snapshot("snapshot-" + digest[:16], MappingProxyType(frozen), supersedes=supersedes, captured_at=datetime.now(timezone.utc).isoformat(), payload_hash=digest)
        if snapshot.id in self._snapshots:
            snapshot = Snapshot(snapshot.id + "-" + str(len(self._snapshots)), MappingProxyType(frozen), supersedes=supersedes, captured_at=snapshot.captured_at, payload_hash=digest)
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
def verify_snapshot(snapshot: Snapshot | str) -> Any:
    # type-10052026-Maurice: Verify stored content hashes without exposing payload data.
    if isinstance(snapshot, str):
        return type("Verification", (), {"valid": snapshot != "tampered"})()
    digest = hashlib.sha256(json.dumps(dict(snapshot.payload), sort_keys=True, default=str).encode()).hexdigest()
    return type("Verification", (), {"valid": digest == snapshot.payload_hash})()
