# type-10052026-Maurice: Provide deterministic synthetic source fixture primitives.
"""Deterministic fixture generation and metadata helpers."""
from __future__ import annotations

import csv
import hashlib
import json
import random
from datetime import date
from pathlib import Path
from typing import Any

from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

try:
    from faker import Faker
except ImportError:  # type-10052026-Maurice: Keep offline bootstrap usable before install.
    Faker = None  # type: ignore[assignment,misc]

_LOGGER = get_logger(__name__)


@trace_call
def raw_hash(payload: Any) -> str:
    """Hash canonical JSON payload without exposing its contents."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


@trace_call
def generate_fixtures(seed: int = 42, data_as_of: str = "2026-01-31", output_dir: str | Path = "data/raw") -> dict[str, Path]:
    """Write byte-stable CRM, billing, and support fixtures and return paths."""
    date.fromisoformat(data_as_of)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    fake = Faker() if Faker is not None else None
    if fake is not None:
        fake.seed_instance(seed)
    suffix = fake.random_int(1000, 9999) if fake is not None else rng.randint(1000, 9999)
    crm = [
        {"source_id": "crm-001", "name": "Juan Dela Cruz", "email": "juan@example.test", "account_id": "acct-001", "data_as_of": data_as_of},
        {"source_id": "crm-002", "name": "Jane Smith", "email": "jane@example.test", "account_id": "acct-002", "data_as_of": data_as_of},
        {"source_id": "crm-dup-001", "name": "Juan Dela Crz", "email": "juan@example.test", "account_id": "acct-001", "data_as_of": data_as_of},
        {"source_id": "crm-invalid-01", "name": "Bad Date", "email": "bad@example.test", "account_id": "acct-003", "data_as_of": "not-a-date"},
    ]
    billing = [
        {"source_id": "billing-001", "account_id": "acct-001", "amount": "125.50", "currency": "USD", "status": "unpaid", "due_date": data_as_of, "data_as_of": data_as_of},
        {"source_id": "billing-002", "account_id": "acct-002", "amount": "50.00", "currency": "USD", "status": "paid", "due_date": data_as_of, "data_as_of": data_as_of},
        {"source_id": "billing-invalid-01", "account_id": "acct-404", "amount": "not-money", "currency": "USD", "status": "unknown", "due_date": data_as_of, "data_as_of": data_as_of},
    ]
    support = [
        {"source_id": "support-001", "customer_email": "juan@example.test", "status": "open", "priority": "high", "text": "Invoice remains unpaid.", "data_as_of": data_as_of},
        {"source_id": "support-002", "customer_email": "orphan@example.test", "status": "open", "priority": "low", "text": "Unmatched request.", "data_as_of": data_as_of},
        {"source_id": f"support-{suffix}", "customer_email": "bad-email", "status": "open", "priority": "high", "text": "Malformed contact.", "data_as_of": data_as_of},
    ]
    crm_path = target / "crm.json"
    billing_path = target / "billing.csv"
    support_path = target / "support.json"
    crm_path.write_text(json.dumps(crm, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    support_path.write_text(json.dumps(support, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    with billing_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(billing[0]))
        writer.writeheader()
        writer.writerows(billing)
    log_event(_LOGGER, "fixtures_generated", source="all", outcome="success")
    return {"crm": crm_path, "billing": billing_path, "support": support_path}
