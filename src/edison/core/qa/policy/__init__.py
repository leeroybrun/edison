"""Validation policy module.

Provides config-driven, pack-extensible validation presets for QA workflows.

This module is the single source of truth for:
- Validation preset definitions (quick, standard, comprehensive)
- Preset inference from file context
- Escalation rules (code changes escalate above quick)
- Evidence requirements per preset

Example:
    from edison.core.qa.policy import ValidationPolicyResolver

    resolver = ValidationPolicyResolver()
    policy = resolver.resolve(files=["src/module.py"])
    print(f"Using preset: {policy.preset.id}")
    print(f"Validators: {policy.preset.validators}")
    print(f"Evidence required: {policy.preset.evidence_required}")
"""
from __future__ import annotations

from .models import ValidationPolicy, ValidationPreset
from .config import PresetConfigLoader
from .inference import PresetInference
from .resolver import ValidationPolicyResolver

__all__ = [
    "ValidationPolicy",
    "ValidationPreset",
    "PresetConfigLoader",
    "PresetInference",
    "ValidationPolicyResolver",
]
