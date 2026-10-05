# type-10052026-Maurice: Keep the TC-032 documentation contract executable.
"""Small, offline documentation inventory used by delivery checks."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from kg.observability.logging import get_logger, log_event
from kg.observability.tracing import trace_call

_LOGGER = get_logger(__name__)
# type-10052026-Maurice: Resolve the checkout, not site-packages, in container images.
_ROOT = Path.cwd().resolve()
_REQUIRED = {
    "ontology": "docs/ontology.md",
    "architecture": "docs/architecture.md",
    "integration": "docs/integration.md",
    "glossary": "docs/glossary.md",
    "quickstart": "docs/quickstart.md",
    "results": "docs/results.md",
    "roadmap": "docs/roadmap.md",
}
_LINK = re.compile(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)")


@dataclass(frozen=True)
class DocumentationContract:
    """Required public documents and unresolved repository-relative links."""

    paths: frozenset[str]
    broken_links: list[str]


@trace_call
def required_documents() -> DocumentationContract:
    """Check the published documentation inventory without network access."""
    broken: list[str] = []
    for relative in _REQUIRED.values():
        document = _ROOT / relative
        if not document.is_file():
            broken.append(relative)
            continue
        for target in _LINK.findall(document.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (_ROOT / target).exists():
                broken.append(f"{relative}->{target}")
    result = DocumentationContract(frozenset(_REQUIRED), sorted(broken))
    log_event(_LOGGER, "documentation_contract_checked", outcome="success" if not broken else "failed")
    return result
