"""Evidence round directory management."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .._utils import sort_round_dirs
from .exceptions import EvidenceError


def find_latest_round_dir(base_dir: Path) -> Optional[Path]:
    """Get latest round-N directory from base_dir."""
    if not base_dir.exists():
        return None

    round_dirs = [p for p in base_dir.glob("round-*") if p.is_dir()]
    rounds = sort_round_dirs(round_dirs)

    return rounds[-1] if rounds else None


def get_round_number(round_dir: Path) -> int:
    """Extract round number from round directory name."""
    try:
        return int(round_dir.name.split("-")[1])
    except (IndexError, ValueError) as e:
        raise EvidenceError(
            f"Invalid round directory name: {round_dir.name}. "
            "Expected format: round-N"
        ) from e


def create_next_round_dir(base_dir: Path) -> Path:
    """Create next round-{N+1} directory and return path."""
    latest = find_latest_round_dir(base_dir)

    if latest is None:
        next_num = 1
    else:
        next_num = get_round_number(latest) + 1

    next_dir = base_dir / f"round-{next_num}"

    try:
        next_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise EvidenceError(
            f"Round directory already exists: {next_dir}. "
            "This suggests a race condition or duplicate operation."
        )
    except Exception as e:
        raise EvidenceError(
            f"Failed to create round directory {next_dir}: {e}"
        ) from e

    return next_dir


def list_round_dirs(base_dir: Path) -> List[Path]:
    """List all round directories for this task."""
    if not base_dir.exists():
        return []

    round_dirs = [p for p in base_dir.glob("round-*") if p.is_dir()]
    return sort_round_dirs(round_dirs)


def resolve_round_dir(base_dir: Path, round_num: Optional[int] = None) -> Optional[Path]:
    """Resolve round directory."""
    if round_num is not None:
        round_dir = base_dir / f"round-{round_num}"
        return round_dir if round_dir.exists() else None
    else:
        return find_latest_round_dir(base_dir)
