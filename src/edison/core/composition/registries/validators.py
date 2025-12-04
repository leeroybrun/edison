#!/usr/bin/env python3
"""Edison Validator Registry.

ValidatorRegistry extends ComposableRegistry[str] for FILE-BASED composition
(like AgentRegistry), while also maintaining config-based roster for metadata.

Architecture:
    CompositionBase → ComposableRegistry → ValidatorRegistry

Features:
- File-based composition: compose_validator() for prompt generation from layers
- Config-based roster: get_all_grouped() for validator metadata from YAML
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Iterable, Optional

from .base import ComposableRegistry
from edison.core.composition.core.paths import CompositionPathResolver


# ---------------------------------------------------------------------------
# Validator Metadata Inference (for validators defined only by id)
# ---------------------------------------------------------------------------

def _discover_validator_file(
    validator_id: str,
    *,
    project_root: Path,
    project_dir: Path,
    bundled_packs_dir: Path,
    active_packs: Iterable[str],
) -> Optional[Path]:
    """Discover validator file using unified path resolution.

    Search order (priority):
    1. Generated validators in project
    2. Project validators
    3. Core validators (global, critical, specialized subdirs)
    4. Pack validators
    """
    resolver = CompositionPathResolver(project_root, "validators")

    # 1. Check generated validators
    generated_path = resolver.project_dir / "_generated" / "validators" / f"{validator_id}.md"
    if generated_path.exists():
        return generated_path

    # 2. Check project validators
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

    # 4. Check pack validators
    for pack in active_packs:
        if bundled_packs_dir and bundled_packs_dir.exists():
            path = bundled_packs_dir / pack / "validators" / f"{validator_id}.md"
            if path.exists():
                return path
        if resolver.bundled_packs_dir.exists():
            path = resolver.bundled_packs_dir / pack / "validators" / f"{validator_id}.md"
            if path.exists():
                return path

    return None


def infer_validator_metadata(
    validator_id: str,
    *,
    project_root: Path,
    project_dir: Path,
    bundled_packs_dir: Path | None = None,
    active_packs: Iterable[str] = (),
) -> Dict[str, Any]:
    """Best-effort metadata extraction for validators defined only by id.

    Falls back to sensible defaults if file not found or parsing fails.
    """
    inferred: Dict[str, Any] = {
        "id": validator_id,
        "name": validator_id.replace("-", " ").title(),
        "model": "codex",
        "triggers": ["*"],
        "alwaysRun": False,
        "blocksOnFail": False,
    }

    path = _discover_validator_file(
        validator_id,
        project_root=project_root,
        project_dir=project_dir,
        bundled_packs_dir=bundled_packs_dir or (project_root / ".edison" / "packs"),
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

    return inferred


def normalize_validator_entries(
    raw_entries: Any,
    *,
    fallback_map: Dict[str, Dict[str, Any]],
    project_root: Path,
    project_dir: Path,
    bundled_packs_dir: Path | None = None,
    active_packs: Iterable[str] = (),
) -> List[Dict[str, Any]]:
    """Normalize roster entries into dicts, enriching ids with inferred metadata."""
    bundled_packs_dir = bundled_packs_dir or (project_root / ".edison" / "packs")
    normalized: List[Dict[str, Any]] = []
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
                        bundled_packs_dir=bundled_packs_dir,
                        active_packs=active_packs,
                    )
                )
    return normalized


# ---------------------------------------------------------------------------
# Roster Collection and Merging
# ---------------------------------------------------------------------------

def _validator_map(roster: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """Build quick lookup map of validator definitions keyed by id."""
    mapping: Dict[str, Dict[str, Any]] = {}
    for entries in roster.values():
        for entry in entries or []:
            if isinstance(entry, dict) and entry.get("id"):
                mapping[entry["id"]] = entry
    return mapping


def _merge_rosters(
    base_roster: Dict[str, List[Dict[str, Any]]],
    override_roster: Dict[str, List[Dict[str, Any]]],
    *,
    project_root: Path,
    project_dir: Path,
    bundled_packs_dir: Path,
    active_packs: Iterable[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """Merge validation + validators rosters."""
    result: Dict[str, List[Dict[str, Any]]] = {}
    base_map = _validator_map(base_roster)

    for bucket in ("global", "critical", "specialized"):
        base_entries = normalize_validator_entries(
            base_roster.get(bucket, []),
            fallback_map=base_map,
            project_root=project_root,
            project_dir=project_dir,
            bundled_packs_dir=bundled_packs_dir,
            active_packs=active_packs,
        )

        override_entries = normalize_validator_entries(
            override_roster.get(bucket, []),
            fallback_map=base_map,
            project_root=project_root,
            project_dir=project_dir,
            bundled_packs_dir=bundled_packs_dir,
            active_packs=active_packs,
        )

        if override_entries:
            seen = {e["id"] for e in override_entries if isinstance(e, dict) and e.get("id")}
            merged: List[Dict[str, Any]] = list(override_entries)
            for entry in base_entries:
                if entry.get("id") not in seen:
                    merged.append(entry)
            result[bucket] = merged
        else:
            result[bucket] = base_entries

    return result


def collect_validators(
    config: Dict[str, Any],
    *,
    project_root: Path,
    project_dir: Path,
    bundled_packs_dir: Path,
    active_packs: Iterable[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """Collect validator roster from merged configuration."""
    validation_cfg = ((config or {}).get("validation", {}) or {})
    validators_cfg = ((config or {}).get("validators", {}) or {})

    base_roster = (validation_cfg.get("roster", {}) or {}) if isinstance(validation_cfg, dict) else {}
    override_roster = (validators_cfg.get("roster", {}) or {}) if isinstance(validators_cfg, dict) else {}

    return _merge_rosters(
        base_roster,
        override_roster,
        project_root=project_root,
        project_dir=project_dir,
        bundled_packs_dir=bundled_packs_dir,
        active_packs=active_packs,
    )


# ---------------------------------------------------------------------------
# ValidatorRegistry - Extends ComposableRegistry (file-based + config-based)
# ---------------------------------------------------------------------------

class ValidatorRegistry(ComposableRegistry[str]):
    """Registry for discovering and composing validators.

    Extends ComposableRegistry for FILE-BASED composition (like AgentRegistry).
    Also maintains config-based roster for metadata.

    Features:
    - compose_validator(): Compose validator prompts from markdown files with layers
    - get_all_grouped(): Get validator metadata from YAML config
    """

    # ComposableRegistry required attributes
    content_type: ClassVar[str] = "validators"
    file_pattern: ClassVar[str] = "*.md"
    strategy_config: ClassVar[Dict[str, Any]] = {
        "enable_sections": True,
        "enable_dedupe": False,
        "enable_template_processing": True,
    }

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize validator registry."""
        super().__init__(project_root)
        self._validators_cache: Optional[Dict[str, Dict[str, Any]]] = None

    # =========================================================================
    # File-based Composition Interface (NEW - like AgentRegistry)
    # =========================================================================

    def compose_validator(self, name: str, packs: Optional[List[str]] = None) -> Optional[str]:
        """Compose validator prompt from layers (like compose_agent).

        Uses MarkdownCompositionStrategy for SECTION/EXTEND markers.

        Args:
            name: Validator name (without extension)
            packs: Optional list of active packs (uses get_active_packs() if None)

        Returns:
            Composed validator prompt string, or None if not found
        """
        return self.compose(name, packs)

    # =========================================================================
    # Config-based Roster Interface (KEEP - existing functionality)
    # =========================================================================

    def _load_validators(self) -> Dict[str, Dict[str, Any]]:
        """Load all validators from configuration."""
        if self._validators_cache is not None:
            return self._validators_cache

        # Load configuration
        config = self.config

        # Get active packs
        packs = self.get_active_packs()

        # Collect validators
        roster = collect_validators(
            config,
            project_root=self.project_root,
            project_dir=self.project_dir,
            bundled_packs_dir=self.bundled_packs_dir,
            active_packs=packs,
        )

        # Build validator map
        validators: Dict[str, Dict[str, Any]] = {}
        for bucket in ("global", "critical", "specialized"):
            for entry in roster.get(bucket, []) or []:
                if isinstance(entry, dict) and entry.get("id"):
                    validators[entry["id"]] = entry

        self._validators_cache = validators
        return validators

    def exists(self, name: str) -> bool:
        """Check if a validator exists in the registry."""
        return name in self._load_validators()

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get validator metadata by name."""
        return self._load_validators().get(name)

    def get_or_raise(self, name: str) -> Dict[str, Any]:
        """Get validator metadata by name, raising if not found."""
        validators = self._load_validators()
        if name not in validators:
            from edison.core.entity import EntityNotFoundError
            raise EntityNotFoundError(
                f"Validator '{name}' not found in registry",
                entity_type="validator",
                entity_id=name,
            )
        return validators[name]

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all validators as a flat list."""
        return list(self._load_validators().values())

    def get_all_grouped(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all validators grouped by tier (global, critical, specialized)."""
        config = self.config
        packs = self.get_active_packs()

        return collect_validators(
            config,
            project_root=self.project_root,
            project_dir=self.project_dir,
            bundled_packs_dir=self.bundled_packs_dir,
            active_packs=packs,
        )

    def list_names(self) -> List[str]:
        """List all validator names."""
        return sorted(self._load_validators().keys())


__all__ = [
    # Metadata functions
    "infer_validator_metadata",
    "normalize_validator_entries",
    # Roster functions
    "collect_validators",
    # Registry
    "ValidatorRegistry",
]
