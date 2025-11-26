from __future__ import annotations

"""Validator roster collection and merging utilities.

Collects validators from merged configuration (validation + validators sections)
and handles roster merging, normalization, and metadata enrichment.
"""

from pathlib import Path
from typing import Dict, List, Iterable, Optional

from .metadata import normalize_validator_entries
from ..paths import PathResolver
from ..paths.project import get_project_config_dir


def _validator_map(roster: Dict[str, List[Dict]]) -> Dict[str, Dict]:
    """Build quick lookup map of validator definitions keyed by id.

    Args:
        roster: Validator roster dict with buckets (global, critical, specialized)

    Returns:
        Dict mapping validator ID to full validator definition
    """
    mapping: Dict[str, Dict] = {}
    for entries in roster.values():
        for entry in entries or []:
            if isinstance(entry, dict) and entry.get("id"):
                mapping[entry["id"]] = entry
    return mapping


def _merge_rosters(
    base_roster: Dict[str, List[Dict]],
    override_roster: Dict[str, List[Dict]],
    *,
    repo_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> Dict[str, List[Dict]]:
    """Merge validation + validators rosters without hardcoded ids.

    Processes each bucket (global, critical, specialized) by:
    1. Normalizing entries (expanding string IDs to full metadata)
    2. Merging override entries over base entries
    3. Preserving order with overrides first

    Args:
        base_roster: Base validator roster (from validation config)
        override_roster: Override roster (from validators config)
        repo_root: Repository root path
        project_dir: Project configuration directory
        packs_dir: Packs directory path
        active_packs: List of active pack names

    Returns:
        Merged validator roster with normalized entries
    """
    result: Dict[str, List[Dict]] = {}
    base_map = _validator_map(base_roster)

    for bucket in ("global", "critical", "specialized"):
        base_entries = normalize_validator_entries(
            base_roster.get(bucket, []),
            fallback_map=base_map,
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=active_packs,
        )

        override_entries = normalize_validator_entries(
            override_roster.get(bucket, []),
            fallback_map=base_map,
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=active_packs,
        )

        if override_entries:
            seen = {e["id"] for e in override_entries if isinstance(e, dict) and e.get("id")}
            merged: List[Dict] = list(override_entries)
            for entry in base_entries:
                if entry.get("id") not in seen:
                    merged.append(entry)
            result[bucket] = merged
        else:
            result[bucket] = base_entries

    return result


def collect_validators(
    config: Dict,
    *,
    repo_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> Dict[str, List[Dict]]:
    """Collect validator roster from merged configuration (validation + validators).

    Extracts validator rosters from both 'validation' and 'validators' config
    sections, merges them (validators overrides validation), and normalizes
    all entries to full metadata dicts.

    Args:
        config: Full configuration dict
        repo_root: Repository root path
        project_dir: Project configuration directory
        packs_dir: Packs directory path
        active_packs: List of active pack names

    Returns:
        Dict with validator buckets: global, critical, specialized
    """
    validation_cfg = ((config or {}).get("validation", {}) or {})
    validators_cfg = ((config or {}).get("validators", {}) or {})

    base_roster = (validation_cfg.get("roster", {}) or {}) if isinstance(validation_cfg, dict) else {}
    override_roster = (validators_cfg.get("roster", {}) or {}) if isinstance(validators_cfg, dict) else {}

    return _merge_rosters(
        base_roster,
        override_roster,
        repo_root=repo_root,
        project_dir=project_dir,
        packs_dir=packs_dir,
        active_packs=active_packs,
    )


class ValidatorRegistry:
    """Discover and access Edison validators from configuration."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        """Initialize validator registry with configuration discovery."""
        self.repo_root: Path = repo_root or PathResolver.resolve_project_root()

        # For Edison's own tests, use bundled data directory instead of .edison/core
        edison_dir = self.repo_root / ".edison"
        core_validators_dir = edison_dir / "core" / "validators"
        if edison_dir.exists() and core_validators_dir.exists():
            self.core_dir = edison_dir / "core"
            self.packs_dir = edison_dir / "packs"
        else:
            # Running within Edison itself - use bundled data
            from edison.data import get_data_path
            self.core_dir = get_data_path("")
            self.packs_dir = get_data_path("packs")

        self.project_dir = get_project_config_dir(self.repo_root)
        self._validators_cache: Optional[Dict[str, Dict]] = None

    def _load_validators(self) -> Dict[str, Dict]:
        """Load all validators from configuration."""
        if self._validators_cache is not None:
            return self._validators_cache

        # Load configuration
        from edison.core.config import ConfigManager
        cfg_mgr = ConfigManager(self.repo_root)
        try:
            config = cfg_mgr.load_config(validate=False)
        except FileNotFoundError:
            config = {}

        # Get active packs
        packs = ((config.get("packs", {}) or {}).get("active", []) or [])
        if not isinstance(packs, list):
            packs = []

        # Collect validators
        roster = collect_validators(
            config,
            repo_root=self.repo_root,
            project_dir=self.project_dir,
            packs_dir=self.packs_dir,
            active_packs=packs,
        )

        # Build validator map
        validators: Dict[str, Dict] = {}
        for bucket in ("global", "critical", "specialized"):
            for entry in roster.get(bucket, []) or []:
                if isinstance(entry, dict) and entry.get("id"):
                    validators[entry["id"]] = entry

        self._validators_cache = validators
        return validators

    def exists(self, name: str) -> bool:
        """Check if a validator exists in the registry."""
        validators = self._load_validators()
        return name in validators

    def get(self, name: str) -> Dict:
        """Get validator metadata by name."""
        validators = self._load_validators()
        if name not in validators:
            raise ValueError(f"Validator '{name}' not found in registry")
        return validators[name]

    def get_all(self) -> Dict[str, List[Dict]]:
        """Get all validators grouped by tier (global, critical, specialized).

        Returns:
            Dict with keys 'global', 'critical', 'specialized', each containing
            a list of validator metadata dicts.
        """
        # Load configuration
        from edison.core.config import ConfigManager
        cfg_mgr = ConfigManager(self.repo_root)
        try:
            config = cfg_mgr.load_config(validate=False)
        except FileNotFoundError:
            config = {}

        # Get active packs
        packs = ((config.get("packs", {}) or {}).get("active", []) or [])
        if not isinstance(packs, list):
            packs = []

        # Collect validators grouped by tier
        roster = collect_validators(
            config,
            repo_root=self.repo_root,
            project_dir=self.project_dir,
            packs_dir=self.packs_dir,
            active_packs=packs,
        )

        return roster


__all__ = [
    "collect_validators",
    "ValidatorRegistry",
]
