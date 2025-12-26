"""Round directory management for QA evidence.

This module centralizes *round* directory mechanics (round-N) so EvidenceService
can stay focused on evidence I/O semantics (bundles, implementation reports,
validator reports) while delegating deterministic filesystem round handling here.

Public API note:
- EvidenceService remains the *only* supported high-level entry point.
- This module is intentionally small and purely functional to avoid stateful
  duplication and to keep EvidenceService DRY.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from edison.core.qa._utils import sort_round_dirs

from .exceptions import EvidenceError


def find_latest_round_dir(evidence_root: Path) -> Optional[Path]:
    """Return the latest round directory under evidence_root, if any."""
    if not evidence_root.exists():
        return None
    round_dirs = [p for p in evidence_root.glob("round-*") if p.is_dir()]
    rounds = sort_round_dirs(round_dirs)
    return rounds[-1] if rounds else None


def get_round_number(round_dir: Path) -> int:
    """Extract the numeric suffix from a round directory name (round-N)."""
    try:
        return int(round_dir.name.split("-")[1])
    except (IndexError, ValueError) as e:
        raise EvidenceError(
            f"Invalid round directory name: {round_dir.name}. Expected format: round-N"
        ) from e


def resolve_round_dir(evidence_root: Path, round_num: Optional[int] = None) -> Optional[Path]:
    """Resolve an existing round directory by number or latest (no creation)."""
    if round_num is not None:
        round_dir = evidence_root / f"round-{round_num}"
        return round_dir if round_dir.exists() else None
    return find_latest_round_dir(evidence_root)


def create_next_round_dir(evidence_root: Path) -> Path:
    """Create the next round directory (round-{N+1}) and return its path."""
    latest = find_latest_round_dir(evidence_root)
    if latest is None:
        next_num = 1
    else:
        next_num = get_round_number(latest) + 1

    next_dir = evidence_root / f"round-{next_num}"
    try:
        next_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as e:
        raise EvidenceError(
            f"Round directory already exists: {next_dir}. "
            "This suggests a race condition or duplicate operation."
        ) from e
    except Exception as e:  # pragma: no cover - defensive
        raise EvidenceError(f"Failed to create round directory {next_dir}: {e}") from e
    return next_dir


def ensure_round_dir(evidence_root: Path, round_num: Optional[int] = None) -> Path:
    """Ensure a round directory exists and return its path.

    Behavior:
    - If round_num is None: return the latest round, else create round-1.
    - If round_num exists: return it.
    - If round_num is the next number: create it.
    - Otherwise: fail closed.
    """
    if not evidence_root.exists():
        evidence_root.mkdir(parents=True, exist_ok=True)

    if round_num is None:
        latest = find_latest_round_dir(evidence_root)
        if latest:
            return latest
        return create_next_round_dir(evidence_root)

    # Specific round requested
    existing = resolve_round_dir(evidence_root, round_num)
    if existing:
        return existing

    latest = find_latest_round_dir(evidence_root)
    next_num = 1
    if latest:
        next_num = get_round_number(latest) + 1

    if round_num == next_num:
        return create_next_round_dir(evidence_root)

    raise EvidenceError(f"Cannot create round {round_num}. Next available is {next_num}.")


def list_round_dirs(evidence_root: Path) -> List[Path]:
    """List all round directories under evidence_root, sorted numerically."""
    if not evidence_root.exists():
        return []
    round_dirs = [p for p in evidence_root.glob("round-*") if p.is_dir()]
    return sort_round_dirs(round_dirs)


__all__ = [
    "find_latest_round_dir",
    "get_round_number",
    "resolve_round_dir",
    "create_next_round_dir",
    "ensure_round_dir",
    "list_round_dirs",
]









