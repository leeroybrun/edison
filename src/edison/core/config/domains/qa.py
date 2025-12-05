"""Domain-specific configuration for QA.

Provides cached access to QA-related configuration including
delegation settings, validation config, and concurrency limits.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseDomainConfig


class QAConfig(BaseDomainConfig):
    """QA configuration access following the DomainConfig pattern.

    Provides structured access to QA-related configuration with repo_root exposure.
    Extends BaseDomainConfig for consistent caching and repo_root handling.

    Configuration is loaded from:
    1. Project config: .edison/config/qa.yaml (if exists)
    2. Bundled defaults: edison.data/config/qa.yaml
    3. Legacy location: validators.yaml (validation section)
    """

    def _config_section(self) -> str:
        return "qa"

    @cached_property
    def delegation_config(self) -> Dict[str, Any]:
        """Return the ``delegation`` section from configuration."""
        section = self._config.get("delegation", {}) or {}
        return section if isinstance(section, dict) else {}

    @cached_property
    def validation_config(self) -> Dict[str, Any]:
        """Return the ``validation`` section from configuration.

        Returns the top-level validation section from ConfigManager,
        which already merges from all sources (bundled defaults, project overrides).
        """
        section = self._config.get("validation", {}) or {}
        return section if isinstance(section, dict) else {}

    @cached_property
    def orchestration_config(self) -> Dict[str, Any]:
        """Return the ``orchestration`` section from configuration.

        Returns the top-level orchestration section from ConfigManager,
        which already merges from all sources (bundled defaults, project overrides).
        """
        section = self._config.get("orchestration", {}) or {}
        return section if isinstance(section, dict) else {}

    def get_delegation_config(self) -> Dict[str, Any]:
        """Return the ``delegation`` section from configuration."""
        return self.delegation_config

    def get_validation_config(self) -> Dict[str, Any]:
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

    def get_required_evidence_files(self) -> List[str]:
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

    # Alias for consistency with module-level function
    def max_concurrent_validators(self) -> int:
        """Alias for get_max_concurrent_validators."""
        return self.get_max_concurrent_validators()

    @cached_property
    def validator_tiers(self) -> List[str]:
        """Return the list of validator tier names from configuration.

        Tiers define logical groupings of validators (e.g., global, critical, specialized).
        Order matters - earlier tiers run first.

        Returns:
            List of tier names in execution order.
        """
        roster = self.validation_config.get("roster", {})
        if isinstance(roster, dict):
            # Default tiers if not explicitly configured
            default_tiers = ["global", "critical", "specialized"]
            # Use configured tier order or default
            tier_order = self.validation_config.get("tierOrder", default_tiers)
            if isinstance(tier_order, list):
                return tier_order
            # Fall back to keys from roster that exist
            return [t for t in default_tiers if t in roster]
        return ["global", "critical", "specialized"]

    @cached_property
    def validation_waves(self) -> List[Dict[str, Any]]:
        """Return the validation waves configuration.

        Waves define execution groups with ordering and failure behavior.

        Returns:
            List of wave configurations with:
            - name: Wave identifier
            - tiers: List of validator tiers in this wave
            - execution: "parallel" or "sequential"
            - continue_on_fail: Whether to run next wave if this fails
            - requires_previous_pass: Whether previous wave must pass
        """
        waves = self.validation_config.get("waves")
        if isinstance(waves, list) and waves:
            return waves
        
        # Default waves based on tier structure
        tiers = self.validator_tiers
        return [
            {
                "name": "blocking",
                "tiers": [t for t in tiers if t in ("global", "critical")],
                "execution": "parallel",
                "continue_on_fail": False,
                "requires_previous_pass": False,
            },
            {
                "name": "specialized",
                "tiers": [t for t in tiers if t not in ("global", "critical")],
                "execution": "parallel",
                "continue_on_fail": True,
                "requires_previous_pass": True,
            },
        ]

    def get_validators_for_tier(self, tier: str) -> List[Dict[str, Any]]:
        """Get validators for a specific tier.

        Args:
            tier: Tier name (e.g., "global", "critical", "specialized")

        Returns:
            List of validator configurations for that tier
        """
        roster = self.validation_config.get("roster", {})
        if isinstance(roster, dict):
            validators = roster.get(tier, [])
            return validators if isinstance(validators, list) else []
        return []

    def get_validators_for_wave(self, wave_name: str) -> List[Dict[str, Any]]:
        """Get all validators for a wave (across all its tiers).

        Args:
            wave_name: Name of the wave

        Returns:
            List of validator configurations for that wave
        """
        waves = self.validation_waves
        wave = next((w for w in waves if w.get("name") == wave_name), None)
        if not wave:
            return []
        
        validators: List[Dict[str, Any]] = []
        for tier in wave.get("tiers", []):
            validators.extend(self.get_validators_for_tier(tier))
        return validators


def load_config(repo_root: Optional[Path] = None) -> QAConfig:
    """Load and return a QAConfig instance.

    Args:
        repo_root: Optional repository root path. Uses auto-detection if None.

    Returns:
        Configured QAConfig instance.
    """
    return QAConfig(repo_root=repo_root)


def load_delegation_config(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load delegation configuration from QA config.

    Args:
        repo_root: Optional repository root path. Uses auto-detection if None.

    Returns:
        Dictionary containing delegation configuration.
    """
    return QAConfig(repo_root=repo_root).get_delegation_config()


def load_validation_config(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load validation configuration from QA config.

    Args:
        repo_root: Optional repository root path. Uses auto-detection if None.

    Returns:
        Dictionary containing validation configuration.
    """
    return QAConfig(repo_root=repo_root).get_validation_config()


def max_concurrent_validators(repo_root: Optional[Path] = None) -> int:
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




