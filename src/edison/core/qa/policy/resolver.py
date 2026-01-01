"""Validation policy resolver.

Single source of truth for resolving validation policies.
Combines preset configuration, file inference, and escalation rules.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import PresetConfigLoader
from .inference import PresetInference
from .models import ValidationPolicy, ValidationPreset


class ValidationPolicyResolver:
    """Resolves validation policy for a given context.

    This is THE single source of truth for validation policy decisions.
    Other components (ValidatorRegistry, EngineRegistry) should delegate
    to this resolver rather than implementing their own preset logic.

    Example:
        resolver = ValidationPolicyResolver()
        policy = resolver.resolve(files=["src/module.py"])
        print(f"Preset: {policy.preset.id}")
        print(f"Validators: {policy.preset.validators}")
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the resolver.

        Args:
            project_root: Project root directory. Auto-detected if not provided.
        """
        self._project_root = project_root
        self._config_loader = PresetConfigLoader(project_root=project_root)
        self._inference = PresetInference(project_root=project_root)

    def resolve(
        self,
        files: list[str] | None = None,
        preset_id: str | None = None,
        task_id: str | None = None,
    ) -> ValidationPolicy:
        """Resolve the validation policy for a given context.

        Resolution priority:
        1. Explicit preset_id if provided (no escalation)
        2. Infer preset from files
        3. Check for escalation from default preset

        Args:
            files: List of modified file paths for inference
            preset_id: Explicit preset ID (overrides inference)
            task_id: Optional task ID for context (future use)

        Returns:
            Resolved ValidationPolicy
        """
        # Priority 1: Explicit preset requested
        if preset_id:
            preset = self._config_loader.get_preset(preset_id)
            if preset:
                return ValidationPolicy(preset=preset)
            # Fall through to inference if preset not found

        # Get default preset from config
        default_preset_id = self._config_loader.get_default_preset_id()
        default_preset = self._config_loader.get_preset(default_preset_id)

        # Priority 2: Infer from files
        files = files or []
        inferred_preset_id = self._inference.infer_preset_from_files(files)
        inferred_preset = self._config_loader.get_preset(inferred_preset_id)

        # Check if we should escalate from default
        if default_preset and inferred_preset:
            if inferred_preset.id != default_preset_id:
                # Escalation occurred
                return ValidationPolicy(
                    preset=inferred_preset,
                    escalated_from=default_preset_id,
                    escalation_reason=self._build_escalation_reason(files, default_preset_id, inferred_preset_id),
                )
            return ValidationPolicy(preset=default_preset)

        # Return inferred if available, otherwise default
        if inferred_preset:
            return ValidationPolicy(preset=inferred_preset)
        if default_preset:
            return ValidationPolicy(preset=default_preset)

        # Fallback: create a minimal preset
        return ValidationPolicy(
            preset=ValidationPreset(
                id="standard",
                name="Standard Validation",
                validators=[],
                evidence_required=[],
            )
        )

    def _build_escalation_reason(
        self,
        files: list[str],
        from_preset: str,
        to_preset: str,
    ) -> str:
        """Build a human-readable escalation reason."""
        if not files:
            return f"Escalated from {from_preset} to {to_preset}"

        # Classify files for the reason
        code_files = [f for f in files if self._inference.classify_file(f) == "code"]
        config_files = [f for f in files if self._inference.classify_file(f) == "config"]

        reasons = []
        if code_files:
            examples = code_files[:3]
            reasons.append(f"code changes: {', '.join(examples)}")
        if config_files:
            examples = config_files[:3]
            reasons.append(f"config changes: {', '.join(examples)}")

        if reasons:
            return f"Escalated from {from_preset} to {to_preset} due to {'; '.join(reasons)}"
        return f"Escalated from {from_preset} to {to_preset}"

    def get_available_presets(self) -> list[str]:
        """Get list of available preset IDs.

        Returns:
            Sorted list of preset identifiers
        """
        return self._config_loader.list_preset_ids()

    def get_preset(self, preset_id: str) -> ValidationPreset | None:
        """Get a specific preset by ID.

        Args:
            preset_id: Preset identifier

        Returns:
            ValidationPreset if found, None otherwise
        """
        return self._config_loader.get_preset(preset_id)


__all__ = ["ValidationPolicyResolver"]
