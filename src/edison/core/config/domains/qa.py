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

    Configuration is loaded from:
    1. Project config: .edison/config/qa.yaml (if exists)
    2. Bundled defaults: edison.data/config/validators.yaml
    """

    def _config_section(self) -> str:
        return "qa"

    @cached_property
    def delegation_config(self) -> dict[str, Any]:
        """Return the ``delegation`` section from configuration."""
        section = self._config.get("delegation", {}) or {}
        return section if isinstance(section, dict) else {}

    @cached_property
    def validation_config(self) -> dict[str, Any]:
        """Return the ``validation`` section from configuration.

        Returns the top-level validation section from ConfigManager,
        which already merges from all sources (bundled defaults, project overrides).
        """
        section = self._config.get("validation", {}) or {}
        return section if isinstance(section, dict) else {}

    @cached_property
    def orchestration_config(self) -> dict[str, Any]:
        """Return the ``orchestration`` section from configuration.

        Returns the top-level orchestration section from ConfigManager,
        which already merges from all sources (bundled defaults, project overrides).
        """
        section = self._config.get("orchestration", {}) or {}
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
                "define it in qa.yaml or .edison/config/qa.yaml"
            )
        return str(session_id)

    def get_required_evidence_files(self) -> list[str]:
        """Return the list of required evidence files from configuration.

        Returns:
            List of required evidence filenames.

        Raises:
            RuntimeError: If validation.requiredEvidenceFiles is not configured.
        """
        files = self.validation_config.get("requiredEvidenceFiles")
        if not files:
            raise RuntimeError(
                "validation.requiredEvidenceFiles missing in configuration; "
                "define it in qa.yaml or .edison/config/qa.yaml"
            )
        if not isinstance(files, list):
            raise RuntimeError(
                f"validation.requiredEvidenceFiles must be a list, got {type(files).__name__}"
            )
        return files

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
                "define it in qa.yaml or .edison/config/qa.yaml"
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

    def get_validators(self) -> dict[str, dict[str, Any]]:
        """Get all validator configurations (flat format).

        Returns:
            Dictionary of validator_id -> validator configuration
        """
        validators = self.validation_config.get("validators", {})
        return validators if isinstance(validators, dict) else {}

    def get_validator(self, validator_id: str) -> dict[str, Any] | None:
        """Get a specific validator configuration.

        Args:
            validator_id: Validator identifier

        Returns:
            Validator configuration dict or None if not found
        """
        return self.get_validators().get(validator_id)

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

        Args:
            wave_name: Name of the wave

        Returns:
            List of validator configurations for that wave
        """
        waves = self.get_waves()
        wave = next((w for w in waves if w.get("name") == wave_name), None)
        if not wave:
            return []

        wave_validator_ids = wave.get("validators", [])
        all_validators = self.get_validators()
        return [
            all_validators[vid]
            for vid in wave_validator_ids
            if vid in all_validators
        ]


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
