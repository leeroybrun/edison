"""Validation policy models.

Defines the core data structures for validation presets and policies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ValidationPreset:
    """A validation preset defining validators and evidence requirements.

    Presets are config-driven and pack-extensible. Each preset specifies:
    - Which validators to run
    - Which evidence files are required
    - Optional escalation to a more thorough preset

    Attributes:
        id: Unique preset identifier (e.g., "quick", "standard", "comprehensive")
        name: Human-readable name
        validators: List of validator IDs to run for this preset
        evidence_required: List of evidence file patterns required
        escalates_to: Optional ID of preset to escalate to
    """

    id: str
    name: str
    validators: list[str] = field(default_factory=list)
    evidence_required: list[str] = field(default_factory=list)
    escalates_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "validators": list(self.validators),
            "evidence_required": list(self.evidence_required),
        }
        if self.escalates_to:
            result["escalates_to"] = self.escalates_to
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationPreset:
        """Create ValidationPreset from dictionary.

        Args:
            data: Dictionary with preset data. Must include 'id'.

        Returns:
            ValidationPreset instance
        """
        preset_id = data.get("id", "")
        name = data.get("name", preset_id.replace("-", " ").title())
        validators = data.get("validators", [])
        evidence_required = data.get("evidence_required", [])
        escalates_to = data.get("escalates_to")

        # Normalize validators list
        if isinstance(validators, list):
            validators = [str(v) for v in validators if v]
        else:
            validators = []

        # Normalize evidence_required list
        if isinstance(evidence_required, list):
            evidence_required = [str(e) for e in evidence_required if e]
        else:
            evidence_required = []

        return cls(
            id=str(preset_id),
            name=str(name),
            validators=validators,
            evidence_required=evidence_required,
            escalates_to=str(escalates_to) if escalates_to else None,
        )


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    """A resolved validation policy for a specific task context.

    Wraps a ValidationPreset with escalation metadata.
    Tracks whether the preset was escalated from a simpler preset
    and why.

    Attributes:
        preset: The resolved ValidationPreset
        escalated_from: ID of the original preset if escalated
        escalation_reason: Reason for escalation if applicable
    """

    preset: ValidationPreset
    escalated_from: str | None = None
    escalation_reason: str | None = None

    @property
    def is_escalated(self) -> bool:
        """Return True if this policy was escalated from a simpler preset."""
        return self.escalated_from is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result: dict[str, Any] = {
            "preset": self.preset.to_dict(),
            "is_escalated": self.is_escalated,
        }
        if self.escalated_from:
            result["escalated_from"] = self.escalated_from
        if self.escalation_reason:
            result["escalation_reason"] = self.escalation_reason
        return result


__all__ = ["ValidationPreset", "ValidationPolicy"]
