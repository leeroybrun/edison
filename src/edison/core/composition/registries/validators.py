from __future__ import annotations

"""Validator roster collection, merging, and metadata utilities.

Collects validators from merged configuration (validation + validators sections)
and handles roster merging, normalization, and metadata enrichment.

Uses CompositionPathResolver for consistent path resolution.

Architecture:
    BaseEntityManager
    └── BaseRegistry
        └── ValidatorRegistry (this module)
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Iterable, Optional

from edison.core.entity import BaseRegistry
from ..core import CompositionPathResolver


# ---------------------------------------------------------------------------
# Validator Metadata Inference
# ---------------------------------------------------------------------------

def _discover_validator_file(
    validator_id: str,
    *,
    project_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> Optional[Path]:
    """Discover validator file using unified path resolution.

    Search order (priority):
    1. Generated validators in project
    2. Project validators (explicit project_dir for test compatibility)
    3. Core validators (global, critical, specialized subdirs)
    4. Pack validators
    """
    resolver = CompositionPathResolver(project_root, "validators")
    
    # 1. Check generated validators
    generated_path = resolver.project_dir / "_generated" / "validators" / f"{validator_id}.md"
    if generated_path.exists():
        return generated_path
    
    # 2. Check project validators (explicit project_dir for compatibility)
    # Also check resolver.project_dir in case they differ
    for proj_dir in [project_dir, resolver.project_dir]:
        if proj_dir and proj_dir.exists():
            for subdir in ("validators/specialized", "validators"):
                path = proj_dir / subdir / f"{validator_id}.md"
                if path.exists():
                    return path
    
    # 3. Check core validators (multiple subdirs)
    core_validators = resolver.core_dir / "validators"
    if core_validators.exists():
        for subdir in ("global", "critical", "specialized"):
            path = core_validators / subdir / f"{validator_id}.md"
            if path.exists():
                return path
    
    # 4. Check pack validators (explicit packs_dir for compatibility)
    for pack in active_packs:
        # Check explicit packs_dir first
        if packs_dir and packs_dir.exists():
            path = packs_dir / pack / "validators" / f"{validator_id}.md"
            if path.exists():
                return path
        # Then check resolver's packs_dir
        if resolver.packs_dir.exists():
            path = resolver.packs_dir / pack / "validators" / f"{validator_id}.md"
            if path.exists():
                return path
    
    return None


def infer_validator_metadata(
    validator_id: str,
    *,
    project_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> Dict:
    """Best-effort metadata extraction for validators defined only by id.

    Uses unified path resolution to search for validator markdown files.
    Falls back to sensible defaults if file not found or parsing fails.

    Args:
        validator_id: Validator identifier (e.g., "python-imports")
        project_root: Project root path
        project_dir: Project configuration directory
        packs_dir: Packs directory path
        active_packs: List of active pack names

    Returns:
        Dict with validator metadata: id, name, model, triggers, alwaysRun, blocksOnFail
    """
    inferred: Dict[str, object] = {
        "id": validator_id,
        "name": validator_id.replace("-", " ").title(),
        "model": "codex",
        "triggers": ["*"],
        "alwaysRun": False,
        "blocksOnFail": False,
    }

    # Use unified discovery with explicit paths for compatibility
    path = _discover_validator_file(
        validator_id,
        project_root=project_root,
        project_dir=project_dir,
        packs_dir=packs_dir,
        active_packs=active_packs,
    )
    
    if not path:
        return inferred

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return inferred

    headers = re.findall(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    for h in headers:
        cleaned = h.strip()
        if cleaned and cleaned.lower() != "core edison principles":
            inferred["name"] = cleaned
            break

    model = re.search(r"\*\*Model\*\*:\s*([^\n*]+)", text)
    if model:
        inferred["model"] = model.group(1).strip()

    triggers_line = re.search(r"\*\*Triggers\*\*:\s*([^\n]+)", text)
    if triggers_line:
        triggers = re.findall(r"`([^`]+)`", triggers_line.group(1))
        if triggers:
            inferred["triggers"] = triggers

    if re.search(r"\*\*Blocks on Fail\*\*:\s*✅\s*YES", text, flags=re.IGNORECASE):
        inferred["blocksOnFail"] = True

    return inferred  # type: ignore[return-value]


def normalize_validator_entries(
    raw_entries,
    *,
    fallback_map: Dict[str, Dict],
    project_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> List[Dict]:
    """Normalize roster entries into dicts, enriching ids with inferred metadata.

    Processes a list of validator entries that may be dicts or strings:
    - Dict entries with 'id' are passed through unchanged
    - String entries are looked up in fallback_map if available
    - Unknown string entries trigger metadata inference
    - Empty strings/None are filtered out

    Args:
        raw_entries: List of validator entries (dicts or strings)
        fallback_map: Map of validator ID to full metadata dict
        project_root: Project root path
        project_dir: Project configuration directory
        packs_dir: Packs directory path
        active_packs: List of active pack names

    Returns:
        List of normalized validator dicts with full metadata
    """
    normalized: List[Dict] = []
    for entry in raw_entries or []:
        if isinstance(entry, dict):
            if "id" in entry:
                normalized.append(entry)
        elif isinstance(entry, str) and entry:
            base = fallback_map.get(entry)
            if base:
                normalized.append(base)
            else:
                normalized.append(
                    infer_validator_metadata(
                        entry,
                        project_root=project_root,
                        project_dir=project_dir,
                        packs_dir=packs_dir,
                        active_packs=active_packs,
                    )
                )
    return normalized


# ---------------------------------------------------------------------------
# Roster Collection and Merging
# ---------------------------------------------------------------------------

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
    project_root: Path,
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
        project_root: Project root path
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
            project_root=project_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=active_packs,
        )

        override_entries = normalize_validator_entries(
            override_roster.get(bucket, []),
            fallback_map=base_map,
            project_root=project_root,
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
    project_root: Path,
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
        project_root: Project root path
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
        project_root=project_root,
        project_dir=project_dir,
        packs_dir=packs_dir,
        active_packs=active_packs,
    )


# ---------------------------------------------------------------------------
# ValidatorRegistry
# ---------------------------------------------------------------------------

class ValidatorRegistry(BaseRegistry[Dict[str, Any]]):
    """Discover and access Edison validators from configuration.
    
    Extends BaseRegistry with config-based validator discovery.
    Uses CompositionPathResolver for consistent path resolution.
    """
    
    entity_type: str = "validator"

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize validator registry with configuration discovery."""
        super().__init__(project_root)

        # Use composition path resolver (SINGLE SOURCE OF TRUTH)
        path_resolver = CompositionPathResolver(self.project_root, "validators")
        self.core_dir = path_resolver.core_dir
        self.packs_dir = path_resolver.packs_dir
        self.project_dir = path_resolver.project_dir
        
        self._validators_cache: Optional[Dict[str, Dict]] = None
    
    # ------- BaseRegistry Interface Implementation -------
    
    def discover_core(self) -> Dict[str, Dict[str, Any]]:
        """Discover core validators.
        
        Note: Validators are loaded from config, not discovered from files.
        This returns an empty dict as validators are managed via config.
        """
        # Validators are config-based, not file-discovered
        return {}
    
    def discover_packs(self, packs: List[str]) -> Dict[str, Dict[str, Any]]:
        """Discover validators from packs.
        
        Note: Validators are loaded from config, not discovered from files.
        """
        return {}
    
    def discover_project(self) -> Dict[str, Dict[str, Any]]:
        """Discover project validators.
        
        Note: Validators are loaded from config, not discovered from files.
        """
        return {}

    def _load_validators(self) -> Dict[str, Dict]:
        """Load all validators from configuration."""
        if self._validators_cache is not None:
            return self._validators_cache

        # Load configuration
        from edison.core.config import ConfigManager
        cfg_mgr = ConfigManager(self.project_root)
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
            project_root=self.project_root,
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

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get validator metadata by name.
        
        Returns:
            Validator metadata dict if found, None otherwise
        """
        validators = self._load_validators()
        return validators.get(name)
    
    def get_or_raise(self, name: str) -> Dict[str, Any]:
        """Get validator metadata by name, raising if not found."""
        validators = self._load_validators()
        if name not in validators:
            from edison.core.entity import EntityNotFoundError
            raise EntityNotFoundError(
                f"Validator '{name}' not found in registry",
                entity_type=self.entity_type,
                entity_id=name,
            )
        return validators[name]

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all validators as a flat list.
        
        Implements BaseRegistry interface.
        """
        return list(self._load_validators().values())
    
    def get_all_grouped(self) -> Dict[str, List[Dict]]:
        """Get all validators grouped by tier (global, critical, specialized).

        For backward compatibility with code expecting grouped results.

        Returns:
            Dict with keys 'global', 'critical', 'specialized', each containing
            a list of validator metadata dicts.
        """
        # Load configuration
        from edison.core.config import ConfigManager
        cfg_mgr = ConfigManager(self.project_root)
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
            project_root=self.project_root,
            project_dir=self.project_dir,
            packs_dir=self.packs_dir,
            active_packs=packs,
        )

        return roster


__all__ = [
    # Metadata functions
    "infer_validator_metadata",
    "normalize_validator_entries",
    # Roster functions
    "collect_validators",
    # Registry
    "ValidatorRegistry",
]



