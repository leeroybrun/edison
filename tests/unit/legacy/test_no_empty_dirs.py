"""Guard against empty directories in the source tree.

This test enforces that all configured roots are free of empty directories,
with allowances for marker files (e.g., `.gitkeep`) defined in YAML config.

STRICT TDD:
- RED: Fails while empty directories exist.
- GREEN: Passes once empty directories are removed or contain allowed markers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from edison.data import read_yaml


def _load_policy() -> tuple[list[Path], set[str]]:
    """Load empty-directory policy from YAML configuration."""

    config = read_yaml("config", "cleanup.yaml")
    policy = config.get("empty_directory_policy") if config else None
    assert policy, "empty_directory_policy missing in config/cleanup.yaml"

    roots = policy.get("roots")
    assert roots, "Configure at least one root directory to scan"

    repo_root = Path(__file__).resolve().parents[3]
    root_paths = [repo_root / Path(root) for root in roots]
    for path in root_paths:
        assert path.exists(), f"Configured root does not exist: {path}"

    allowed_markers = set(policy.get("allowed_markers", []))
    assert allowed_markers, "Define allowed_markers (e.g., .gitkeep) in cleanup.yaml"

    return root_paths, allowed_markers


def _is_effectively_empty(directory: Path, allowed_markers: set[str]) -> bool:
    """Return True when the directory has no entries aside from allowed markers."""

    children = list(directory.iterdir())
    if not children:
        return True

    marker_names = {name for name in allowed_markers}
    non_marker_children = [child for child in children if child.name not in marker_names]

    # If anything besides marker files exists, the directory is not empty
    if non_marker_children:
        return False

    # Directory contains only marker files → treat as intentionally kept
    return False


def test_no_empty_directories_in_configured_roots() -> None:
    roots, allowed_markers = _load_policy()

    empty_dirs: list[str] = []
    repo_root = Path(__file__).resolve().parents[3]

    for root in roots:
        for path in root.rglob("*"):
            if not path.is_dir():
                continue
            if _is_effectively_empty(path, allowed_markers):
                empty_dirs.append(str(path.relative_to(repo_root)))

    if empty_dirs:
        error_lines = [
            "Empty directories detected (no entries other than allowed markers):",
            *sorted(empty_dirs),
            "\nAdd a marker file (e.g., .gitkeep) or remove the directory.",
        ]
        pytest.fail("\n".join(error_lines))
