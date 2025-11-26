from __future__ import annotations

"""
Guideline discovery module.

Responsibilities:
- Discover guideline markdown files across core, packs, project overlays, and
  any additional guideline directories in the repository.
- Categorize guidelines by layer (core/pack/project/other)
- Track pack ownership for pack-specific guidelines

This module is intentionally dependency-light so it can be used both from
pytest and from standalone CLI scripts.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Literal

from ..includes import _repo_root as _composition_repo_root
from ...paths.project import get_project_config_dir


GuidelineCategory = Literal["core", "pack", "project", "other"]


@dataclass
class GuidelineRecord:
    """Represents a single guideline markdown file."""

    path: Path
    category: GuidelineCategory
    pack: Optional[str] = None  # for category == "pack"

    def relpath(self, repo_root: Optional[Path] = None) -> Path:
        root = repo_root or _composition_repo_root()
        try:
            return self.path.relative_to(root)
        except ValueError:
            return self.path


def _repo_root() -> Path:
    """Delegate to composition engine root resolution."""
    return _composition_repo_root()


def discover_guidelines(repo_root: Optional[Path] = None) -> List[GuidelineRecord]:
    """Discover guideline files across the repository.

    Categories:
    - core:    .edison/core/guidelines/**/*.md
    - pack:    .edison/packs/*/guidelines/**/*.md
    - project:  <project_config_dir>/guidelines/**/*.md (including overlays)
    - other:   any additional guidelines/*.md directories not covered above
    """
    root = repo_root or _repo_root()
    records: List[GuidelineRecord] = []

    # Core guidelines
    core_dir = root / ".edison" / "core" / "guidelines"
    if core_dir.exists():
        for path in sorted(core_dir.rglob("*.md")):
            if path.name == "README.md":
                continue
            records.append(GuidelineRecord(path=path, category="core"))

    # Pack guidelines
    packs_root = root / ".edison" / "packs"
    if packs_root.exists():
        for pack_dir in sorted(p for p in packs_root.iterdir() if p.is_dir()):
            gdir = pack_dir / "guidelines"
            if not gdir.exists():
                continue
            for path in sorted(gdir.rglob("*.md")):
                if path.name == "README.md":
                    continue
                records.append(
                    GuidelineRecord(path=path, category="pack", pack=pack_dir.name)
                )

    # project project guidelines (including overlays)
    project_dir = get_project_config_dir(root) / "guidelines"
    if project_dir.exists():
        for path in sorted(project_dir.rglob("*.md")):
            if "README.md" == path.name:
                continue
            records.append(GuidelineRecord(path=path, category="project"))

    # Any other guidelines directories in the repo
    known_roots = {
        core_dir.resolve(),
        *(r.path.parent.resolve() for r in records if r.category in ("pack", "project")),
    }
    for gdir in root.rglob("guidelines"):
        if not gdir.is_dir():
            continue
        if any(str(gdir).startswith(str(known)) for known in known_roots):
            continue
        for path in sorted(gdir.glob("*.md")):
            if path.name == "README.md":
                continue
            records.append(GuidelineRecord(path=path, category="other"))

    return records


__all__ = [
    "GuidelineRecord",
    "GuidelineCategory",
    "discover_guidelines",
]
