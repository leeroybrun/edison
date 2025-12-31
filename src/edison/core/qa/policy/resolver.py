"""Validation policy resolver - THE canonical place for preset selection.

This is the single source of truth for resolving validation policies.
All components (validator registry, evidence analysis, CLI) should
delegate to this resolver for preset selection and requirements.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Optional

from edison.core.qa.policy.models import ValidationPolicy, ValidationPreset
from edison.core.qa.policy.config import PresetConfigLoader
from edison.core.qa.policy.inference import PresetInference


class ValidationPolicyResolver:
    """Resolves validation policies for tasks.

    This is THE single canonical place for:
    - Preset selection (explicit or inferred)
    - Validator roster filtering based on preset
    - Evidence requirement determination

    All other components should delegate to this resolver rather than
    implementing their own preset/evidence logic.

    Example:
        resolver = ValidationPolicyResolver()

        # Infer preset from changed files
        policy = resolver.resolve_for_task("T001")

        # Use explicit preset
        policy = resolver.resolve_for_task("T001", preset_name="standard")

        # Get validators to run
        print(policy.validators)

        # Get required evidence
        print(policy.required_evidence)
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize policy resolver.

        Args:
            project_root: Optional project root path. Auto-detected if not provided.
        """
        self._project_root = project_root
        self._config_loader: Optional[PresetConfigLoader] = None
        self._inference: Optional[PresetInference] = None

    @property
    def project_root(self) -> Path:
        """Get project root, resolving lazily if needed."""
        if self._project_root is None:
            from edison.core.utils.paths import PathResolver
            self._project_root = PathResolver.resolve_project_root()
        return self._project_root

    @cached_property
    def config_loader(self) -> PresetConfigLoader:
        """Get config loader (lazy init)."""
        return PresetConfigLoader(project_root=self.project_root)

    @cached_property
    def inference(self) -> PresetInference:
        """Get preset inference engine (lazy init)."""
        return PresetInference(project_root=self.project_root)

    @cached_property
    def _presets(self) -> dict[str, ValidationPreset]:
        """Load and cache all presets."""
        return self.config_loader.load_presets()

    def resolve_for_task(
        self,
        task_id: str,
        session_id: Optional[str] = None,
        preset_name: Optional[str] = None,
    ) -> ValidationPolicy:
        """Resolve validation policy for a task.

        If preset_name is provided, uses that preset directly.
        Otherwise, infers the preset from the task's changed files.

        Args:
            task_id: Task identifier
            session_id: Optional session ID for file context
            preset_name: Optional explicit preset name (skips inference)

        Returns:
            ValidationPolicy with resolved preset and task context

        Raises:
            ValueError: If explicit preset_name is unknown
        """
        # Get changed files for the task
        changed_files = self._get_changed_files(task_id, session_id)

        # Resolve preset
        if preset_name:
            # Explicit preset requested
            preset = self._presets.get(preset_name)
            if not preset:
                available = ", ".join(sorted(self._presets.keys()))
                raise ValueError(
                    f"Unknown preset '{preset_name}'. Available presets: {available}"
                )
            return ValidationPolicy(
                preset=preset,
                task_id=task_id,
                changed_files=changed_files,
                inferred_preset_name=preset_name,
                was_escalated=False,
            )

        # Infer preset from changed files
        result = self.inference.infer_preset(changed_files)

        # Get the inferred preset
        preset = self._presets.get(result.preset_name)
        if not preset:
            # Fallback to standard if inferred preset not configured
            preset = self._presets.get("standard")
            if not preset:
                # Ultimate fallback - create a minimal preset
                preset = ValidationPreset(
                    name="standard",
                    validators=["global-codex"],
                    required_evidence=[],
                    blocking_validators=["global-codex"],
                )

        return ValidationPolicy(
            preset=preset,
            task_id=task_id,
            changed_files=changed_files,
            inferred_preset_name=result.preset_name,
            was_escalated=result.was_escalated,
            escalation_reason=result.escalation_reason,
        )

    def get_preset(self, name: str) -> Optional[ValidationPreset]:
        """Get a specific preset by name.

        Args:
            name: Preset name

        Returns:
            ValidationPreset if found, None otherwise
        """
        return self._presets.get(name)

    def list_presets(self) -> list[str]:
        """List all available preset names.

        Returns:
            Sorted list of preset names
        """
        return sorted(self._presets.keys())

    def _get_changed_files(
        self,
        task_id: str,
        session_id: Optional[str] = None,
    ) -> list[str]:
        """Get changed files for a task.

        Uses FileContextService to get files from implementation report or git.

        Args:
            task_id: Task identifier
            session_id: Optional session ID

        Returns:
            List of changed file paths
        """
        try:
            from edison.core.context.files import FileContextService

            service = FileContextService(project_root=self.project_root)
            ctx = service.get_for_task(task_id, session_id)
            return ctx.all_files
        except Exception:
            return []


__all__ = ["ValidationPolicyResolver"]
