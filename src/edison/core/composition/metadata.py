from __future__ import annotations

"""Validator metadata inference utilities.

Infers validator metadata (name, model, triggers, blocking) from validator
markdown files when validators are defined only by ID. Provides sensible
defaults when files are missing or parsing fails.
"""

import re
from pathlib import Path
from typing import Dict, List, Iterable


def infer_validator_metadata(
    validator_id: str,
    *,
    repo_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> Dict:
    """Best-effort metadata extraction for validators defined only by id.

    Searches for validator markdown files in multiple locations (project,
    repo core, packs) and parses metadata from the content. Falls back to
    sensible defaults if file not found or parsing fails.

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

    def _first_existing(paths: Iterable[Path]) -> Path | None:
        for p in paths:
            if p.exists():
                return p
        return None

    candidate_paths = [
        project_dir / "_generated" / "validators" / f"{validator_id}.md",
        project_dir / "validators" / "specialized" / f"{validator_id}.md",
        repo_root / ".edison" / "core" / "validators" / "specialized" / f"{validator_id}.md",
    ]

    for pack in active_packs:
        candidate_paths.append(packs_dir / pack / "validators" / f"{validator_id}.md")

    path = _first_existing(candidate_paths)
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
