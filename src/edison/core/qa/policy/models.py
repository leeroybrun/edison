"""Validation policy data models.

Defines the core data structures for validation presets and policies.
These are pure data classes with no external dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class ValidationPreset:
    """Configuration for a validation preset.

    A preset defines which validators to run and what evidence is required.
    Presets are defined in YAML config and can be extended by packs/projects.

    Attributes:
        name: Unique preset identifier (e.g., "quick", "standard", "strict")
        validators: List of validator IDs to include in this preset
        required_evidence: List of evidence file patterns required for this preset
        blocking_validators: List of validator IDs that must pass (blocks promotion).
            Defaults to all validators in the preset if not specified.
        description: Optional human-readable description
    """

    name: str
    validators: list[str]
    required_evidence: list[str]
    blocking_validators: Optional[list[str]] = None
    description: str = ""

    def __post_init__(self) -> None:
        """Set defaults after initialization."""
        # If blocking_validators is not provided (None), default to all validators.
        # An explicit empty list is valid (advisory-only preset).
        if self.blocking_validators is None:
            object.__setattr__(self, "blocking_validators", list(self.validators))
        else:
            object.__setattr__(self, "blocking_validators", list(self.blocking_validators))


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    """Resolved validation policy for a specific task.

    Contains the resolved preset along with task context information
    used to determine which preset was selected.

    Attributes:
        preset: The resolved ValidationPreset to apply
        task_id: Task identifier this policy applies to
        changed_files: List of files that were changed (used for inference)
        inferred_preset_name: The initially inferred preset name
        was_escalated: Whether the preset was escalated from initial inference
        escalation_reason: If escalated, the reason for escalation
    """

    preset: ValidationPreset
    task_id: str
    changed_files: list[str] = field(default_factory=list)
    inferred_preset_name: str = ""
    was_escalated: bool = False
    escalation_reason: str = ""

    @property
    def blocking_validators(self) -> list[str]:
        """Return the list of blocking validators from the preset."""
        blocking = self.preset.blocking_validators
        if blocking is None:
            return list(self.preset.validators)
        return list(blocking)

    @property
    def required_evidence(self) -> list[str]:
        """Return the list of required evidence files from the preset."""
        return self.preset.required_evidence

    @property
    def validators(self) -> list[str]:
        """Return the list of all validators from the preset."""
        return self.preset.validators


__all__ = ["ValidationPreset", "ValidationPolicy"]
