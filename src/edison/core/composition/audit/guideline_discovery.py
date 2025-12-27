from __future__ import annotations

"""
Guideline discovery module.

Responsibilities:
- Discover guideline markdown files across core, packs, project overlays, and
  any additional guideline directories in the repository.
- Categorize guidelines by layer (core/pack/project/other)
- Track pack ownership for pack-specific guidelines

Uses CompositionPathResolver for consistent path resolution.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Literal

from edison.core.utils.paths import PathResolver
from ..core import CompositionPathResolver


GuidelineCategory = Literal["core", "pack", "project", "other"]


@dataclass
class GuidelineRecord:
    """Represents a single guideline markdown file."""

    path: Path
    category: GuidelineCategory
    pack: Optional[str] = None  # for category == "pack"

    def relpath(self, repo_root: Optional[Path] = None) -> Path:
        root = repo_root or PathResolver.resolve_project_root()
        try:
            return self.path.relative_to(root)
        except ValueError:
            return self.path


def _repo_root() -> Path:
    """Canonical repo root resolution."""
    return PathResolver.resolve_project_root()


def discover_guidelines(repo_root: Optional[Path] = None) -> List[GuidelineRecord]:
    """Discover guideline files across the repository.

    Uses CompositionPathResolver for consistent path resolution.

    Categories:
    - core:    edison.data/guidelines/**/*.md (bundled defaults)
    - pack:    <any-pack-root>/<pack>/guidelines/**/*.md
    - project: <any-overlay-layer>/guidelines/**/*.md (company/user/project, including overlays)
    """
    root = repo_root or _repo_root()
    
    # Use composition path resolver for consistent path resolution
    path_resolver = CompositionPathResolver(root, "guidelines")
    core_dir = path_resolver.core_dir / "guidelines"
    pack_roots = [r.path for r in path_resolver.pack_roots]
    overlay_layers = [p for _lid, p in path_resolver.overlay_layers]
    
    records: List[GuidelineRecord] = []

    # Core guidelines
    if core_dir.exists():
        for path in sorted(core_dir.rglob("*.md")):
            if path.name == "README.md":
                continue
            records.append(GuidelineRecord(path=path, category="core"))

    # Pack guidelines (all pack roots)
    for packs_root in pack_roots:
        if not packs_root.exists():
            continue
        for pack_dir in sorted(p for p in packs_root.iterdir() if p.is_dir()):
            gdir = pack_dir / "guidelines"
            if not gdir.exists():
                continue
            for path in sorted(gdir.rglob("*.md")):
                if path.name == "README.md":
                    continue
                records.append(GuidelineRecord(path=path, category="pack", pack=pack_dir.name))

    # Overlay layer guidelines (company/user/project; including overlays/)
    for layer_dir in overlay_layers:
        gdir = layer_dir / "guidelines"
        if not gdir.exists():
            continue
        for path in sorted(gdir.rglob("*.md")):
            if "README.md" == path.name:
                continue
            records.append(GuidelineRecord(path=path, category="project"))

    return records


__all__ = [
    "GuidelineRecord",
    "GuidelineCategory",
    "discover_guidelines",
]
