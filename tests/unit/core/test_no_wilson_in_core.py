"""T-055: Core must not contain Wilson-specific content.

The core Edison package (`src/edison/`) must remain project-agnostic. Any
Wilson-specific strings belong in the project overlay (`.edison/`). This test
fails fast when "wilson" appears in core Python files or bundled resources.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.utils.paths.resolver import PathResolver

FORBIDDEN_TOKEN = "wilson"
ALLOWED_SUFFIXES = {
    ".py",
    ".pyi",
    ".md",
    ".mdx",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".txt",
}


def _iter_files(root: Path, *, suffixes: set[str]) -> list[Path]:
    """Return text-like files under root filtered by suffix."""

    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in suffixes:
            files.append(path)
    return files


def _find_violations(paths: list[Path]) -> list[Path]:
    violations: list[Path] = []
    for path in paths:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if FORBIDDEN_TOKEN in content.lower():
            violations.append(path)
    return violations


def test_core_python_files_are_wilson_free() -> None:
    """No core Python file should contain Wilson-specific strings."""

    repo_root = PathResolver.resolve_project_root()
    core_root = repo_root / "src" / "edison"
    python_files = _iter_files(core_root, suffixes={".py", ".pyi"})

    assert python_files, "No Python files discovered under src/edison"

    violations = _find_violations(python_files)
    assert not violations, (
        "Wilson-specific content must live in project overlays (.edison/),"
        " not core Python modules. Remove references from:\n"
        + "\n".join(f"- {path.relative_to(repo_root)}" for path in violations)
    )


def test_core_resources_are_wilson_free() -> None:
    """Guardrail: bundled core resources must not embed Wilson content."""

    repo_root = PathResolver.resolve_project_root()
    core_root = repo_root / "src" / "edison"
    resource_files = _iter_files(core_root, suffixes=ALLOWED_SUFFIXES)

    assert resource_files, "No core resources found to validate"

    violations = _find_violations(resource_files)
    assert not violations, (
        "Wilson-specific content belongs in the project overlay (.edison/). "
        "Remove or relocate from core resources:\n"
        + "\n".join(f"- {path.relative_to(repo_root)}" for path in violations)
    )
