from __future__ import annotations

from ...legacy_guard import enforce_no_legacy_project_root

enforce_no_legacy_project_root("lib.qa.validator")

from .base import (
    _SAFE_INCLUDE_RE,
    _is_safe_path,
    _read_text_safe,
    _resolve_include_path,
    process_validator_template,
    run_validator,
    validate_dimension_weights,
)
from .delegation import enhance_delegation_hint, simple_delegation_hint
from .roster import build_validator_roster
from .external import ExternalValidatorRunner

__all__ = [
    "validate_dimension_weights",
    "simple_delegation_hint",
    "enhance_delegation_hint",
    "build_validator_roster",
    "process_validator_template",
    "run_validator",
    "ExternalValidatorRunner",
]
