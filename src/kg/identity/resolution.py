# type-10052026-Maurice: Implement deterministic, auditable identity resolution.
"""Transparent blocking and weighted identity resolution.

The resolver accepts mappings rather than connector-specific objects so source
adapters can be added later without changing this seam.  Raw identity values
are never sent to logs; they are used only for bounded, deterministic scoring.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from importlib import import_module
from typing import Any, Callable, Iterable, Mapping, Sequence, cast

from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

_rapid_ratio: Callable[[str, str], float] | None
try:  # pragma: no cover - optional acceleration
    _rapid_ratio = cast(Callable[[str, str], float], getattr(import_module("rapidfuzz.fuzz"), "ratio"))
except (ImportError, AttributeError):  # pragma: no cover - exercised in the offline baseline
    _rapid_ratio = None

LOGGER = get_logger(__name__)
RESOLVER_VERSION = "identity-v1"
DEFAULT_THRESHOLDS = {"auto": 0.90, "review": 0.70}
_NON_WORD = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Decision:
    """A threshold decision; ``same_as`` is only present for auto matches."""

    decision: str
    same_as: str | None


@dataclass(frozen=True)
class Assignment:
    """Auditable result of assigning one candidate to canonical people."""

    accepted: bool
    link: str | None
    error_artifact: Mapping[str, str] | None


@dataclass(frozen=True)
class CanonicalPerson:
    """Stable Person hub independent from any source record."""

    person_id: str
    entity_type: str = "Person"


class ResolutionAssertion(dict[str, Any]):
    """Mapping assertion that also supports the contract's set-subset syntax."""

    # type-10052026-Maurice: Preserve mapping compatibility while making required-key checks explicit.
    @trace_call
    def __ge__(self, other: object) -> bool:
        if isinstance(other, set):
            return other <= set(self.keys())
        return False


@trace_call
def _normalize(value: Any) -> str:
    """Normalize a bounded identity field without emitting its value."""
    return _NON_WORD.sub("", str(value or "").lower())


@trace_call
def _email(value: Any) -> str:
    """Normalize an email address for exact matching."""
    return str(value or "").strip().casefold()


@trace_call
def _phonetic(value: Any) -> str:
    """Return a deterministic Soundex-like code for blocking and evidence."""
    text = _normalize(value)
    if not text:
        return ""
    first = text[0].upper()
    groups = {"bfpv": "1", "cgjkqsxz": "2", "dt": "3", "l": "4", "mn": "5", "r": "6"}
    codes = {char: code for chars, code in groups.items() for char in chars}
    tail = []
    previous = ""
    for char in text[1:]:
        code = codes.get(char, "")
        if code and code != previous:
            tail.append(code)
        previous = code
    return (first + "".join(tail) + "000")[:4]


@trace_call
def _similar(left: str, right: str) -> float:
    """Compute a reproducible 0..1 fuzzy similarity."""
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if _rapid_ratio is not None:
        return float(_rapid_ratio(left, right)) / 100.0
    return SequenceMatcher(None, left, right).ratio()


@trace_call
def _person_id(person: Mapping[str, Any]) -> str:
    """Use a supplied canonical ID or derive a stable non-PII hub ID."""
    supplied = person.get("person_id") or person.get("id")
    if supplied:
        return str(supplied)
    basis = "|".join(_normalize(person.get(field)) for field in ("name", "email", "phone"))
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"person-{digest}"


@trace_call
def _blocks(record: Mapping[str, Any]) -> set[str]:
    """Produce transparent blocking keys; empty values are never blocks."""
    name = _normalize(record.get("name"))
    tokens = name.split()
    keys = set()
    if _email(record.get("email")):
        keys.add("email:" + _email(record.get("email")))
    phone = _normalize(record.get("phone"))
    if phone:
        keys.add("phone:" + phone[-7:])
    if tokens:
        keys.add("phonetic:" + _phonetic(tokens[-1]))
        keys.add("name-prefix:" + tokens[0][:3])
    return keys


@trace_call
def _features(record: Mapping[str, Any], person: Mapping[str, Any]) -> dict[str, float]:
    """Calculate weighted evidence features, each bounded to 0..1."""
    name = _similar(_normalize(record.get("name")), _normalize(person.get("name")))
    email_left, email_right = _email(record.get("email")), _email(person.get("email"))
    email = 1.0 if email_left and email_left == email_right else 0.0
    phone_left, phone_right = _normalize(record.get("phone")), _normalize(person.get("phone"))
    phone = 1.0 if phone_left and phone_right and phone_left[-7:] == phone_right[-7:] else 0.0
    left_name = _normalize(record.get("name")).split()
    right_name = _normalize(person.get("name")).split()
    phonetic = 1.0 if left_name and right_name and _phonetic(left_name[-1]) == _phonetic(right_name[-1]) else 0.0
    return {"name_fuzzy": round(name, 6), "email_exact": email, "phone_exact": phone, "name_phonetic": phonetic}


@trace_call
def canonical_person(person: Mapping[str, Any]) -> CanonicalPerson:
    """Create a source-independent canonical Person hub identity."""
    return CanonicalPerson(_person_id(person))


@trace_call
def block_candidates(record: Mapping[str, Any], canonical_persons: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return only candidates sharing transparent blocking keys."""
    keys = _blocks(record)
    return [dict(person) for person in canonical_persons if keys.intersection(_blocks(person))]


@trace_call
def score_candidate(record: Mapping[str, Any], person: Mapping[str, Any]) -> dict[str, Any]:
    """Return weighted score and feature evidence without making a decision."""
    evidence = _features(record, person)
    score = round(0.55 * evidence["name_fuzzy"] + 0.25 * evidence["email_exact"] + 0.10 * evidence["phone_exact"] + 0.10 * evidence["name_phonetic"], 6)
    return {"score": score, "feature_evidence": evidence}


@trace_call
def decide(score: float, thresholds: Mapping[str, float] | None = None, strong_fields_agree: bool = False) -> Decision:
    """Apply inclusive auto/review thresholds and fail closed below review."""
    values = dict(DEFAULT_THRESHOLDS)
    values.update(thresholds or {})
    if score >= values["auto"] and strong_fields_agree:
        return Decision("auto_match", "sameAs")
    if score >= values["review"]:
        return Decision("review_required", None)
    return Decision("unresolved", None)


@trace_call
def assign(candidate: str, people: Sequence[str]) -> Assignment:
    """Reject duplicate canonical assignments rather than publishing a link."""
    unique = tuple(dict.fromkeys(str(person) for person in people))
    if len(unique) != 1:
        return Assignment(False, None, {"code": "duplicate_canonical_assignment", "candidate": str(candidate)})
    return Assignment(True, unique[0], None)


@trace_call
def resolve(
    source_records: Iterable[Mapping[str, Any]],
    run_id: str,
    canonical_persons: Iterable[Mapping[str, Any]] | None = None,
    thresholds: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Resolve source records into canonical Person hubs with evidence."""
    persons = list(canonical_persons or [])
    records = list(source_records)
    if not persons:
        persons = [{"person_id": _person_id(record), **dict(record)} for record in records]
    index: dict[str, list[Mapping[str, Any]]] = {}
    for person in persons:
        for key in _blocks(person):
            index.setdefault(key, []).append(person)
    output: list[dict[str, Any]] = []
    for record in records:
        candidates: dict[str, Mapping[str, Any]] = {}
        for key in _blocks(record):
            for person in index.get(key, []):
                candidates[_person_id(person)] = person
        if not candidates:
            candidates = {_person_id(person): person for person in persons}
        ranked = []
        for person in candidates.values():
            evidence = _features(record, person)
            score = round(0.55 * evidence["name_fuzzy"] + 0.25 * evidence["email_exact"] + 0.10 * evidence["phone_exact"] + 0.10 * evidence["name_phonetic"], 6)
            strong = evidence["email_exact"] == 1.0 or (evidence["name_fuzzy"] >= 0.95 and evidence["phone_exact"] == 1.0)
            ranked.append((score, person, evidence, strong))
        ranked.sort(key=lambda item: (-item[0], _person_id(item[1])))
        score, person, evidence, strong = ranked[0]
        decision = decide(score, thresholds, strong)
        output.append(ResolutionAssertion({
            "candidate": str(record.get("source_record_id", "")),
            "person": _person_id(person),
            "score": score,
            "feature_evidence": evidence,
            "thresholds": dict(thresholds or DEFAULT_THRESHOLDS),
            "decision": decision.decision,
            "same_as": decision.same_as,
            "resolver_version": RESOLVER_VERSION,
            "run_id": run_id,
            "blocking": sorted(_blocks(record)),
        }))
    log_event(LOGGER, "identity_resolution_completed", run_id=run_id, outcome="success", source="identity", elapsed_ms=0)
    return output
