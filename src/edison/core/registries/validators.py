"""Validator metadata registry.

Provides read-only access to validator configuration from YAML.
Uses the flat validator format with engines and waves.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from edison.core.config import ConfigManager
from edison.core.entity.base import EntityId

from ._base import BaseRegistry


@dataclass
class ValidatorMetadata:
    """Validator metadata from configuration."""

    id: str
    name: str
    engine: str
    wave: str
    triggers: list[str] = field(default_factory=list)
    blocking: bool = True
    always_run: bool = False
    fallback_engine: str = ""
    prompt: str = ""
    timeout: int = 300
    context7_required: bool = False
    context7_packages: list[str] = field(default_factory=list)
    focus: list[str] = field(default_factory=list)

    @property
    def zen_role(self) -> str:
        """Get the zenRole for this validator (inferred from ID)."""
        return f"validator-{self.id}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["zen_role"] = self.zen_role
        return result


def _collect_validators_from_config(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Collect validators from flat configuration format.

    Args:
        config: Full configuration dict

    Returns:
        Dict mapping validator_id to validator config
    """
    validation_cfg = config.get("validation", {}) or {}
    validators = validation_cfg.get("validators", {})
    if isinstance(validators, dict):
        return validators
    return {}


def _collect_validators_grouped(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Collect validators grouped by wave.

    Args:
        config: Full configuration dict

    Returns:
        Dict mapping wave to list of validator configs
    """
    all_validators = _collect_validators_from_config(config)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for validator_id, validator_cfg in all_validators.items():
        # Ensure id is set
        validator_cfg = dict(validator_cfg)
        validator_cfg["id"] = validator_id

        wave = validator_cfg.get("wave", "")
        if wave not in grouped:
            grouped[wave] = []
        grouped[wave].append(validator_cfg)

    return grouped


class ValidatorRegistry(BaseRegistry[ValidatorMetadata]):
    """Registry for validator metadata.

    Reads validator configuration from YAML.
    Uses the flat validator format with engines and waves.

    Example:
        registry = ValidatorRegistry(project_root)
        validators = registry.get_all_grouped()
        for wave, validators in validators.items():
            print(f"{wave}: {len(validators)} validators")
    """

    entity_type: str = "validator"

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize validator registry.

        Args:
            project_root: Project root directory. Auto-detected if not provided.
        """
        super().__init__(project_root)
        self._cfg_mgr = ConfigManager(repo_root=self.project_root)
        self._cache: dict[str, ValidatorMetadata] | None = None
        self._grouped_cache: dict[str, list[ValidatorMetadata]] | None = None

    def _load_config(self) -> dict[str, Any]:
        """Load configuration."""
        return self._cfg_mgr.load_config(validate=False)

    def _normalize_entry(self, entry: dict[str, Any]) -> ValidatorMetadata:
        """Convert config entry to ValidatorMetadata.

        Args:
            entry: Raw config entry

        Returns:
            ValidatorMetadata instance
        """
        validator_id = entry.get("id", "")

        return ValidatorMetadata(
            id=validator_id,
            name=entry.get("name", validator_id.replace("-", " ").title()),
            engine=entry.get("engine", ""),
            wave=entry.get("wave", ""),
            triggers=entry.get("triggers", []),
            blocking=entry.get("blocking", True),
            always_run=entry.get("always_run", False),
            fallback_engine=entry.get("fallback_engine", ""),
            prompt=entry.get("prompt", ""),
            timeout=entry.get("timeout", 300),
            context7_required=entry.get("context7_required", False),
            context7_packages=entry.get("context7_packages", []),
            focus=entry.get("focus", []),
        )

    def _load_all(self) -> dict[str, ValidatorMetadata]:
        """Load all validators (cached).

        Returns:
            Dict mapping validator ID to metadata
        """
        if self._cache is not None:
            return self._cache

        config = self._load_config()
        all_validators = _collect_validators_from_config(config)

        self._cache = {}
        for validator_id, entry in all_validators.items():
            # Ensure id is set
            entry_with_id = dict(entry)
            entry_with_id["id"] = validator_id
            metadata = self._normalize_entry(entry_with_id)
            self._cache[metadata.id] = metadata

        return self._cache

    def _load_grouped(self) -> dict[str, list[ValidatorMetadata]]:
        """Load validators grouped by wave (cached).

        Returns:
            Dict mapping wave to list of validators
        """
        if self._grouped_cache is not None:
            return self._grouped_cache

        config = self._load_config()
        grouped = _collect_validators_grouped(config)

        self._grouped_cache = {}
        for wave, entries in grouped.items():
            self._grouped_cache[wave] = []
            for entry in entries:
                metadata = self._normalize_entry(entry)
                self._grouped_cache[wave].append(metadata)

        return self._grouped_cache

    def exists(self, entity_id: EntityId) -> bool:
        """Check if a validator exists.

        Args:
            entity_id: Validator ID

        Returns:
            True if validator exists
        """
        return entity_id in self._load_all()

    def get(self, entity_id: EntityId) -> ValidatorMetadata | None:
        """Get validator metadata by ID.

        Args:
            entity_id: Validator ID

        Returns:
            ValidatorMetadata if found, None otherwise
        """
        return self._load_all().get(entity_id)

    def get_all(self) -> list[ValidatorMetadata]:
        """Get all validator metadata.

        Returns:
            List of all validator metadata, sorted by ID
        """
        return sorted(self._load_all().values(), key=lambda v: v.id)

    def get_all_grouped(self) -> dict[str, list[ValidatorMetadata]]:
        """Get validators grouped by wave.

        Returns:
            Dict mapping wave to validators
        """
        return self._load_grouped()

    def get_by_wave(self, wave: str) -> list[ValidatorMetadata]:
        """Get validators for a specific wave.

        Args:
            wave: Wave name (e.g., "critical", "comprehensive")

        Returns:
            List of validators in that wave
        """
        return self._load_grouped().get(wave, [])

    def list_names(self) -> list[str]:
        """List all validator IDs.

        Returns:
            Sorted list of validator IDs
        """
        return sorted(self._load_all().keys())


__all__ = ["ValidatorRegistry", "ValidatorMetadata"]
