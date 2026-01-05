"""Domain-specific configuration for QA.

Provides cached access to QA-related configuration including
delegation settings, validation config, engines, validators, and waves.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any

from ..base import BaseDomainConfig


class QAConfig(BaseDomainConfig):
    """QA configuration access following the DomainConfig pattern.

    Provides structured access to QA-related configuration with repo_root exposure.
    Extends BaseDomainConfig for consistent caching and repo_root handling.

    This domain reads the top-level configuration keys:
    - ``validation`` (validators, engines, artifact paths, evidence requirements)
    - ``orchestration`` (validator concurrency, timeouts)

    Edison historically used ``qa`` as a nested config key; the current config
    layout is top-level and file-oriented (e.g., ``config/validation.yaml``).
    """

    def _config_section(self) -> str:
        # Retained for BaseDomainConfig compatibility; this domain overrides
        # ``section`` to read from the full merged configuration.
        return "qa"

    @cached_property
    def section(self) -> dict[str, Any]:
        """Return the full merged configuration dict for QA-related lookups."""
        cfg = self._config or {}
        return cfg if isinstance(cfg, dict) else {}

    @cached_property
    def delegation_config(self) -> dict[str, Any]:
        """Return the ``delegation`` section from configuration."""
        section = self.section.get("delegation", {}) or {}
        return section if isinstance(section, dict) else {}

    @cached_property
    def validation_config(self) -> dict[str, Any]:
        """Return the ``validation`` section from configuration.

        Returns the top-level validation section from ConfigManager,
        which already merges from all sources (bundled defaults, project overrides).
        """
        section = self.section.get("validation", {}) or {}
        return section if isinstance(section, dict) else {}

    @cached_property
    def orchestration_config(self) -> dict[str, Any]:
        """Return the ``orchestration`` section from configuration.

        Returns the top-level orchestration section from ConfigManager,
        which already merges from all sources (bundled defaults, project overrides).
        """
        section = self.section.get("orchestration", {}) or {}
        return section if isinstance(section, dict) else {}

    def get_delegation_config(self) -> dict[str, Any]:
        """Return the ``delegation`` section from configuration."""
        return self.delegation_config

    def get_validation_config(self) -> dict[str, Any]:
        """Return the ``validation`` section from configuration."""
        return self.validation_config

    def get_validation_session_id(self) -> str:
        """Return the default session ID for validation transactions.

        Returns:
            Session ID string to use for validation operations.

        Raises:
            RuntimeError: If validation.defaultSessionId is not configured.
        """
        session_id = self.validation_config.get("defaultSessionId")
        if not session_id:
            raise RuntimeError(
                "validation.defaultSessionId missing in configuration; "
                "define it in validation.yaml or <project-config-dir>/config/validation.yaml"
            )
        return str(session_id)

    def get_required_evidence_files(self) -> list[str]:
        """Return the list of required evidence files from configuration.

        Returns:
            List of required evidence filenames.

        Raises:
            RuntimeError: If required evidence files are not configured.
        """
        evidence = self.validation_config.get("evidence", {}) or {}
        files = None
        if isinstance(evidence, dict):
            files = evidence.get("requiredFiles")

        if not files:
            # Fail closed: evidence requirements must be explicitly configured.
            raise RuntimeError(
                    "Required evidence files missing in configuration; "
                    "define validation.evidence.requiredFiles in validation.yaml "
                    "(or override in <project-config-dir>/config/validation.yaml)"
            )
        if not isinstance(files, list):
            raise RuntimeError(
                f"validation.evidence.requiredFiles must be a list, got {type(files).__name__}"
            )

        normalized = [str(f).strip() for f in files if f]
        if normalized:
            return normalized

        # Final fallback: derive from evidence.files mapping (if present).
        files_by_name = evidence.get("files") if isinstance(evidence, dict) else None
        if isinstance(files_by_name, dict) and files_by_name:
            preferred_order = ["type-check", "lint", "test", "build"]
            derived: list[str] = []
            for key in preferred_order:
                v = files_by_name.get(key)
                if v:
                    derived.append(str(v).strip())
            if not derived:
                derived = [str(v).strip() for v in files_by_name.values() if v]
            derived = [d for d in derived if d]
            if derived:
                return derived

        raise RuntimeError(
            "Required evidence files resolved to an empty list; "
            "set validation.evidence.requiredFiles in validation.yaml"
        )

    def get_max_concurrent_validators(self) -> int:
        """Return the global validator concurrency cap from configuration.

        Returns:
            Maximum number of concurrent validators.

        Raises:
            RuntimeError: If orchestration.maxConcurrentAgents is not configured.
        """
        value = self.orchestration_config.get("maxConcurrentAgents")
        if value is None:
            raise RuntimeError(
                "orchestration.maxConcurrentAgents missing in configuration; "
                "define it under orchestration.maxConcurrentAgents in config YAML"
            )
        return int(value)

    def max_concurrent_validators(self) -> int:
        """Alias for get_max_concurrent_validators."""
        return self.get_max_concurrent_validators()

    # Engine-based API methods

    @cached_property
    def engines_config(self) -> dict[str, Any]:
        """Return the engines configuration.

        Engines define execution backends (CLI tools, delegation, etc.).

        Returns:
            Dictionary of engine_id -> engine configuration
        """
        engines = self.validation_config.get("engines", {})
        return engines if isinstance(engines, dict) else {}

    def get_engines(self) -> dict[str, dict[str, Any]]:
        """Get all engine configurations.

        Returns:
            Dictionary of engine_id -> engine configuration
        """
        return self.engines_config

    def get_engine(self, engine_id: str) -> dict[str, Any] | None:
        """Get a specific engine configuration.

        Args:
            engine_id: Engine identifier

        Returns:
            Engine configuration dict or None if not found
        """
        return self.engines_config.get(engine_id)

    @cached_property
    def _validator_registry(self) -> Any:
        """Get ValidatorRegistry instance (cached).

        Returns:
            ValidatorRegistry instance for delegation
        """
        from edison.core.registries.validators import ValidatorRegistry
        return ValidatorRegistry(project_root=self.repo_root)

    def get_validators(self) -> dict[str, dict[str, Any]]:
        """Get all validator configurations (flat format).

        Delegates to ValidatorRegistry for single source of truth.

        Returns:
            Dictionary of validator_id -> validator configuration
        """
        return {v.id: v.to_dict() for v in self._validator_registry.get_all()}

    def get_validator(self, validator_id: str) -> dict[str, Any] | None:
        """Get a specific validator configuration.

        Delegates to ValidatorRegistry for single source of truth.

        Args:
            validator_id: Validator identifier

        Returns:
            Validator configuration dict or None if not found
        """
        v = self._validator_registry.get(validator_id)
        return v.to_dict() if v else None

    def get_waves(self) -> list[dict[str, Any]]:
        """Get wave configurations.

        Waves define execution groups with ordering and failure behavior.

        Returns:
            List of wave configurations with:
            - name: Wave identifier
            - validators: List of validator IDs in this wave
            - execution: "parallel" or "sequential"
            - continue_on_fail: Whether to run next wave if this fails
            - requires_previous_pass: Whether previous wave must pass
        """
        waves = self.validation_config.get("waves")
        if isinstance(waves, list) and waves:
            return waves
        return []

    def get_validators_for_wave(self, wave_name: str) -> list[dict[str, Any]]:
        """Get all validators for a wave.

        Delegates to ValidatorRegistry for single source of truth.

        Args:
            wave_name: Name of the wave

        Returns:
            List of validator configurations for that wave
        """
        return [v.to_dict() for v in self._validator_registry.get_by_wave(wave_name)]

    @cached_property
    def _defaults(self) -> dict[str, Any]:
        """Return the ``validation.defaults`` section from configuration."""
        defaults = self.validation_config.get("defaults", {})
        return defaults if isinstance(defaults, dict) else {}

    def get_default_wave(self) -> str:
        """Return the default wave for validators without explicit wave assignment.

        Returns:
            Default wave name (e.g., "comprehensive")
        """
        wave = self._defaults.get("wave")
        if not wave:
            return "comprehensive"  # Last-resort fallback
        return str(wave)


def load_config(repo_root: Path | None = None) -> QAConfig:
    """Load and return a QAConfig instance.

    Args:
        repo_root: Optional repository root path. Uses auto-detection if None.

    Returns:
        Configured QAConfig instance.
    """
    return QAConfig(repo_root=repo_root)


def load_delegation_config(repo_root: Path | None = None) -> dict[str, Any]:
    """Load delegation configuration from QA config.

    Args:
        repo_root: Optional repository root path. Uses auto-detection if None.

    Returns:
        Dictionary containing delegation configuration.
    """
    return QAConfig(repo_root=repo_root).get_delegation_config()


def load_validation_config(repo_root: Path | None = None) -> dict[str, Any]:
    """Load validation configuration from QA config.

    Args:
        repo_root: Optional repository root path. Uses auto-detection if None.

    Returns:
        Dictionary containing validation configuration.
    """
    return QAConfig(repo_root=repo_root).get_validation_config()


def max_concurrent_validators(repo_root: Path | None = None) -> int:
    """Get the maximum number of concurrent validators.

    Args:
        repo_root: Optional repository root path. Uses auto-detection if None.

    Returns:
        Maximum concurrent validator count.
    """
    return QAConfig(repo_root=repo_root).get_max_concurrent_validators()


__all__ = [
    "QAConfig",
    "load_config",
    "load_delegation_config",
    "load_validation_config",
    "max_concurrent_validators",
]
