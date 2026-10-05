# type-10052026-Maurice: Keep governance exports narrow so publication cannot bypass validation.
"""Validation and quarantine boundary."""

from kg.governance.validation import ValidationResult, validate_and_quarantine, validate_fixtures

__all__ = ["ValidationResult", "validate_and_quarantine", "validate_fixtures"]
