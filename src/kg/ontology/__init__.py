# type-10052026-Maurice: Expose the governed ontology helpers without importing adapters.
"""Ontology vocabulary and deterministic URI helpers."""

from kg.ontology.provenance import required_fields
from kg.ontology.uris import canonical_uri

__all__ = ["canonical_uri", "required_fields"]
