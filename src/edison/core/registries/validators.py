"""Validator metadata registry.

Provides read-only access to validator roster from YAML configuration.
This is separate from composition - it only reads metadata, not composed content.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.entity.base import EntityId
from edison.core.config import ConfigManager
from edison.core.composition.core.paths import CompositionPathResolver
from edison.core.utils.paths import get_project_config_dir

from ._base import BaseRegistry


@dataclass
class ValidatorMetadata:
    """Validator metadata from configuration."""
    
    id: str
    name: str
    model: str
    triggers: List[str]
    blocks_on_fail: bool
    tier: str  # global, critical, specialized
    always_run: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


def _get_configured_tiers(config: Dict[str, Any]) -> List[str]:
    """Get tier names from configuration.
    
    Args:
        config: Full configuration dict
        
    Returns:
        List of tier names in execution order
    """
    validation_cfg = config.get("validation", {}) or {}
    tier_order = validation_cfg.get("tierOrder")
    if isinstance(tier_order, list) and tier_order:
        return tier_order
    # Default tiers for backward compatibility
    return ["global", "critical", "specialized"]


def _collect_validators_from_config(
    config: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    """Collect validator roster from configuration.
    
    Args:
        config: Full configuration dict
        
    Returns:
        Dict mapping tier to list of validator dicts
    """
    validation_cfg = config.get("validation", {}) or {}
    validators_cfg = config.get("validators", {}) or {}
    
    base_roster = validation_cfg.get("roster", {}) or {}
    override_roster = validators_cfg.get("roster", {}) or {}
    
    # Get tiers from config instead of hardcoding
    tiers = _get_configured_tiers(config)
    
    # Merge rosters - override takes precedence
    result: Dict[str, List[Dict[str, Any]]] = {}
    
    for tier in tiers:
        base_entries = base_roster.get(tier, []) or []
        override_entries = override_roster.get(tier, []) or []
        
        # Normalize entries (can be just IDs or full dicts)
        entries: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()
        
        # Override entries first (higher priority)
        for entry in override_entries:
            if isinstance(entry, str):
                entry = {"id": entry}
            if isinstance(entry, dict) and entry.get("id"):
                entries.append(entry)
                seen_ids.add(entry["id"])
        
        # Then base entries (if not overridden)
        for entry in base_entries:
            if isinstance(entry, str):
                entry = {"id": entry}
            if isinstance(entry, dict) and entry.get("id"):
                if entry["id"] not in seen_ids:
                    entries.append(entry)
        
        result[tier] = entries
    
    return result


class ValidatorRegistry(BaseRegistry[ValidatorMetadata]):
    """Registry for validator metadata.
    
    Reads validator roster from YAML configuration.
    Does NOT compose validators - use GenericRegistry for composition.
    
    Example:
        registry = ValidatorRegistry(project_root)
        validators = registry.get_all_grouped()
        for tier, validators in validators.items():
            print(f"{tier}: {len(validators)} validators")
    """
    
    entity_type: str = "validator"
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize validator registry.
        
        Args:
            project_root: Project root directory. Auto-detected if not provided.
        """
        super().__init__(project_root)
        self._cfg_mgr = ConfigManager(repo_root=self.project_root)
        self._cache: Optional[Dict[str, ValidatorMetadata]] = None
        self._grouped_cache: Optional[Dict[str, List[ValidatorMetadata]]] = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration."""
        return self._cfg_mgr.load_config(validate=False)
    
    def _normalize_entry(self, entry: Dict[str, Any], tier: str) -> ValidatorMetadata:
        """Convert config entry to ValidatorMetadata.
        
        Args:
            entry: Raw config entry
            tier: Validator tier (global, critical, specialized)
            
        Returns:
            ValidatorMetadata instance
        """
        validator_id = entry.get("id", "")
        return ValidatorMetadata(
            id=validator_id,
            name=entry.get("name", validator_id.replace("-", " ").title()),
            model=entry.get("model", "codex"),
            triggers=entry.get("triggers", ["*"]),
            blocks_on_fail=entry.get("blocksOnFail", False),
            tier=tier,
            always_run=entry.get("alwaysRun", False),
        )
    
    def _load_all(self) -> Dict[str, ValidatorMetadata]:
        """Load all validators (cached).
        
        Returns:
            Dict mapping validator ID to metadata
        """
        if self._cache is not None:
            return self._cache
        
        config = self._load_config()
        roster = _collect_validators_from_config(config)
        
        self._cache = {}
        for tier, entries in roster.items():
            for entry in entries:
                metadata = self._normalize_entry(entry, tier)
                self._cache[metadata.id] = metadata
        
        return self._cache
    
    def _load_grouped(self) -> Dict[str, List[ValidatorMetadata]]:
        """Load validators grouped by tier (cached).
        
        Returns:
            Dict mapping tier to list of validators
        """
        if self._grouped_cache is not None:
            return self._grouped_cache
        
        config = self._load_config()
        roster = _collect_validators_from_config(config)
        
        self._grouped_cache = {}
        for tier, entries in roster.items():
            self._grouped_cache[tier] = [
                self._normalize_entry(entry, tier) for entry in entries
            ]
        
        return self._grouped_cache
    
    def exists(self, entity_id: EntityId) -> bool:
        """Check if a validator exists.
        
        Args:
            entity_id: Validator ID
            
        Returns:
            True if validator exists
        """
        return entity_id in self._load_all()
    
    def get(self, entity_id: EntityId) -> Optional[ValidatorMetadata]:
        """Get validator metadata by ID.
        
        Args:
            entity_id: Validator ID
            
        Returns:
            ValidatorMetadata if found, None otherwise
        """
        return self._load_all().get(entity_id)
    
    def get_all(self) -> List[ValidatorMetadata]:
        """Get all validator metadata.
        
        Returns:
            List of all validator metadata, sorted by ID
        """
        return sorted(self._load_all().values(), key=lambda v: v.id)
    
    def get_all_grouped(self) -> Dict[str, List[ValidatorMetadata]]:
        """Get validators grouped by tier.
        
        Returns:
            Dict mapping tier (global, critical, specialized) to validators
        """
        return self._load_grouped()
    
    def get_by_tier(self, tier: str) -> List[ValidatorMetadata]:
        """Get validators for a specific tier.
        
        Args:
            tier: One of "global", "critical", "specialized"
            
        Returns:
            List of validators in that tier
        """
        return self._load_grouped().get(tier, [])
    
    def list_names(self) -> List[str]:
        """List all validator IDs.
        
        Returns:
            Sorted list of validator IDs
        """
        return sorted(self._load_all().keys())


__all__ = ["ValidatorRegistry", "ValidatorMetadata"]
