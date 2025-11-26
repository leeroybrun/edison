from __future__ import annotations

"""Validator metadata inference utilities.

Infers validator metadata (name, model, triggers, blocking) from validator
markdown files when validators are defined only by ID. Provides sensible
defaults when files are missing or parsing fails.

Uses UnifiedPathResolver for consistent path resolution.
"""

import re
from pathlib import Path
from typing import Dict, List, Iterable, Optional

from .unified import UnifiedPathResolver


def _discover_validator_file(
    validator_id: str,
    *,
    repo_root: Path,
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
    resolver = UnifiedPathResolver(repo_root, "validators")
    
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
    repo_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> Dict:
    """Best-effort metadata extraction for validators defined only by id.

    Uses unified path resolution to search for validator markdown files.
    Falls back to sensible defaults if file not found or parsing fails.

    Args:
        validator_id: Validator identifier (e.g., "python-imports")
        repo_root: Repository root path
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
        repo_root=repo_root,
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
    repo_root: Path,
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
        repo_root: Repository root path
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
                        repo_root=repo_root,
                        project_dir=project_dir,
                        packs_dir=packs_dir,
                        active_packs=active_packs,
                    )
                )
    return normalized


__all__ = [
    "infer_validator_metadata",
    "normalize_validator_entries",
]
