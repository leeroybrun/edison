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
    1. Project config: .edison/config/qa.yml (if exists)
    2. Bundled defaults: edison.data/config/qa.yml
    3. Legacy location: validators.yaml (validation section)
    """

    def _config_section(self) -> str:
        return "qa"

    @cached_property
    def _bundled_qa_config(self) -> Dict[str, Any]:
        """Load bundled QA configuration from qa.yml."""
        from edison.data import read_yaml
        try:
            return read_yaml("config", "qa.yml") or {}
        except Exception:
            return {}

    @cached_property
    def _legacy_validation_config(self) -> Dict[str, Any]:
        """Load legacy validation config from validators.yaml."""
        from edison.data import read_yaml
        try:
            validators_cfg = read_yaml("config", "validators.yaml") or {}
            return validators_cfg.get("validation", {}) or {}
        except Exception:
            return {}

    @cached_property
    def delegation_config(self) -> Dict[str, Any]:
        """Return the ``delegation`` section from configuration."""
        section = self._config.get("delegation", {}) or {}
        return section if isinstance(section, dict) else {}

    @cached_property
    def validation_config(self) -> Dict[str, Any]:
        """Return the ``validation`` section from configuration.

        Merges from multiple sources in priority order:
        1. BaseDomainConfig section (project overrides)
        2. Bundled qa.yml validation section
        3. Legacy validators.yaml validation section
        """
        # Start with bundled qa.yml
        bundled = self._bundled_qa_config.get("validation", {}) or {}

        # Merge with legacy validators.yaml
        if self._legacy_validation_config:
            from edison.core.utils.merge import deep_merge
            bundled = deep_merge(bundled, self._legacy_validation_config)

        # Finally merge with project overrides from section
        project_section = self.section.get("validation", {}) or {}
        if project_section:
            from edison.core.utils.merge import deep_merge
            bundled = deep_merge(bundled, project_section)

        return bundled

    @cached_property
    def orchestration_config(self) -> Dict[str, Any]:
        """Return the ``orchestration`` section from configuration."""
        # Try bundled qa.yml first
        bundled = self._bundled_qa_config.get("orchestration", {}) or {}

        # Merge with project overrides
        project_section = self.section.get("orchestration", {}) or {}
        if project_section:
            from edison.core.utils.merge import deep_merge
            bundled = deep_merge(bundled, project_section)

        # Fallback to root orchestration config if needed
        if not bundled:
            bundled = self._config.get("orchestration", {}) or {}

        return bundled

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
                "define it in qa.yml or .edison/config/qa.yml"
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
                "define it in qa.yml or .edison/config/qa.yml"
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
                "define it in qa.yml or .edison/config/qa.yml"
            )
        return int(value)

    # Alias for consistency with module-level function
    def max_concurrent_validators(self) -> int:
        """Alias for get_max_concurrent_validators."""
        return self.get_max_concurrent_validators()


__all__ = [
    "QAConfig",
]



