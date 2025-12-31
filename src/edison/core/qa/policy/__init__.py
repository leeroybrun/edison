"""Validation policy module - single source of truth for validation requirements.

This module provides config-driven, pack-extensible validation presets.
The policy resolver is THE canonical place for preset selection and
validation requirements enforcement.

Usage:
    from edison.core.qa.policy import ValidationPolicyResolver, ValidationPolicy

    resolver = ValidationPolicyResolver()
    policy = resolver.resolve_for_task("T001")
    print(f"Using preset: {policy.preset.name}")
    print(f"Validators: {policy.preset.validators}")
    print(f"Required evidence: {policy.required_evidence}")
"""
from __future__ import annotations

from edison.core.qa.policy.models import (
    ValidationPreset,
    ValidationPolicy,
)
from edison.core.qa.policy.config import PresetConfigLoader
from edison.core.qa.policy.inference import PresetInference, PresetInferenceResult
from edison.core.qa.policy.resolver import ValidationPolicyResolver

__all__ = [
    "ValidationPreset",
    "ValidationPolicy",
    "PresetConfigLoader",
    "PresetInference",
    "PresetInferenceResult",
    "ValidationPolicyResolver",
]
