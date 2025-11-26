from __future__ import annotations

"""Validator roster collection and merging utilities.

Collects validators from merged configuration (validation + validators sections)
and handles roster merging, normalization, and metadata enrichment.
"""

from pathlib import Path
from typing import Dict, List, Iterable

from .metadata import normalize_validator_entries


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


__all__ = [
    "collect_validators",
]
