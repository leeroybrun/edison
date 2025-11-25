#!/usr/bin/env python3
from __future__ import annotations

"""
Edison Guideline Composition Engine

Builds final guideline documents from layered sources:
  Core Guidelines  →  Pack Guidelines  →  Project Overrides

Features:
  - Discovery registry for guideline files across layers
  - Include resolution via lib.composition.resolve_includes
  - DRY enforcement using 12-word shingles (headings/code ignored)
  - Layer priority: Core < Packs (dependency order) < Project overrides

The public API is intentionally small and mirrors the prompt
composition engine where practical.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from edison.core.utils.git import get_repo_root
from .paths.project import get_project_config_dir
from .composition import resolve_includes, ComposeError  # type: ignore
from .composition_utils import (  # type: ignore
    dry_duplicate_report,
    ENGINE_VERSION,
    _strip_headings_and_code,
    _tokenize,
    _shingles,
)


# -----------------------
# Root & IO helpers
# -----------------------

def _repo_root() -> Path:
    """Resolve project root via shared git utility."""
    return get_repo_root()


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Guideline file not found: {path}")
    return path.read_text(encoding="utf-8")


def _split_paragraphs(text: str) -> List[str]:
    """Split text into logical paragraphs, preserving intra-paragraph newlines."""
    paragraphs: List[str] = []
    buf: List[str] = []
    for line in text.splitlines():
        if line.strip() == "":
            if buf:
                paragraphs.append("\n".join(buf).rstrip())
                buf = []
        else:
            buf.append(line.rstrip())
    if buf:
        paragraphs.append("\n".join(buf).rstrip())
    return paragraphs


def _paragraph_shingles(paragraph: str, *, k: int = 12) -> Set[Tuple[str, ...]]:
    """Compute 12‑word shingles for a paragraph, ignoring headings/code."""
    cleaned = _strip_headings_and_code(paragraph)
    tokens = _tokenize(cleaned)
    return _shingles(tokens, k=k)


@dataclass
class GuidelinePaths:
    core: Optional[Path]
    packs: Dict[str, Path]  # pack name → path
    project: Optional[Path]


@dataclass
class GuidelineCompositionResult:
    name: str
    text: str
    paths: GuidelinePaths
    duplicate_report: Dict


class GuidelineRegistry:
    """Registry for discovering and composing guidelines across layers."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = repo_root or _repo_root()
        self.core_dir = self.repo_root / ".edison" / "core" / "guidelines"
        self.packs_dir = self.repo_root / ".edison" / "packs"
        project_dir = get_project_config_dir(self.repo_root)
        self.project_guidelines_dir = project_dir / "guidelines"

    # ---------- Discovery ----------
    def core_path(self, name: str) -> Optional[Path]:
        """Find a core guideline by name anywhere under .edison/core/guidelines."""
        pattern = f"{name}.md"
        matches = sorted(self.core_dir.rglob(pattern)) if self.core_dir.exists() else []
        return matches[0] if matches else None

    def pack_paths(self, name: str, packs: List[str]) -> List[Path]:
        """Find pack guideline files (supports nested directories)."""
        paths: List[Path] = []
        for pack in packs:
            pdir = self.packs_dir / pack / "guidelines"
            if not pdir.exists():
                continue
            paths.extend(sorted(pdir.rglob(f"{name}.md")))
        return paths

    def project_override_path(self, name: str) -> Optional[Path]:
        """Find project guideline overrides (supports nested directories)."""
        if not self.project_guidelines_dir.exists():
            return None
        matches = sorted(self.project_guidelines_dir.rglob(f"{name}.md"))
        return matches[0] if matches else None

    def all_names(self, packs: List[str], *, include_project: bool = True) -> List[str]:
        """Return all guideline names discovered across layers (recursive)."""
        names: Set[str] = set()

        if self.core_dir.exists():
            for f in self.core_dir.rglob("*.md"):
                if f.is_file():
                    names.add(f.stem)

        for pack in packs:
            pdir = self.packs_dir / pack / "guidelines"
            if not pdir.exists():
                continue
            for f in pdir.rglob("*.md"):
                if f.is_file():
                    names.add(f.stem)

        if include_project and self.project_guidelines_dir.exists():
            for f in self.project_guidelines_dir.rglob("*.md"):
                if f.is_file():
                    names.add(f.stem)

        return sorted(names)

    def get_subfolder(self, name: str, packs: List[str]) -> Optional[str]:
        """
        Determine the subfolder for a guideline based on its source location.

        Priority (high→low):
          1. Project override location
          2. Pack location (first pack that has it)
          3. Core location

        Returns:
          - Subfolder name relative to guidelines root (e.g., "agents", "shared")
          - None if guideline is in root directory
        """
        # Check project override first
        if self.project_guidelines_dir.exists():
            matches = sorted(self.project_guidelines_dir.rglob(f"{name}.md"))
            if matches:
                rel_path = matches[0].parent.relative_to(self.project_guidelines_dir)
                subfolder = str(rel_path) if str(rel_path) != "." else None
                return subfolder

        # Check packs (in order)
        for pack in packs:
            pdir = self.packs_dir / pack / "guidelines"
            if not pdir.exists():
                continue
            matches = sorted(pdir.rglob(f"{name}.md"))
            if matches:
                rel_path = matches[0].parent.relative_to(pdir)
                subfolder = str(rel_path) if str(rel_path) != "." else None
                return subfolder

        # Check core
        if self.core_dir.exists():
            matches = sorted(self.core_dir.rglob(f"{name}.md"))
            if matches:
                rel_path = matches[0].parent.relative_to(self.core_dir)
                subfolder = str(rel_path) if str(rel_path) != "." else None
                return subfolder

        return None

    # ---------- Composition ----------
    def _resolve_layer_text(self, path: Optional[Path]) -> str:
        if path is None:
            return ""
        raw = _read_text(path)
        expanded, _deps = resolve_includes(raw, path)
        return expanded

    def _dedupe_layers(
        self,
        *,
        name: str,
        core_text: str,
        pack_texts: Dict[str, str],
        project_text: str,
        k: int = 12,
    ) -> Tuple[str, Dict[str, str], str]:
        """Deduplicate paragraphs across layers using 12‑word shingles.

        Priority (high→low):
          1. Project overrides
          2. Packs (last pack wins on duplicates)
          3. Core
        """
        # Split into paragraphs
        core_pars = _split_paragraphs(core_text)
        pack_pars: Dict[str, List[str]] = {
            pack: _split_paragraphs(txt) for pack, txt in pack_texts.items()
        }
        project_pars = _split_paragraphs(project_text)

        # Track shingles seen so far; process from highest to lowest priority.
        seen: Set[Tuple[str, ...]] = set()

        # Project overrides (highest)
        project_keep: List[bool] = [True] * len(project_pars)
        for idx, para in enumerate(project_pars):
            shingles = _paragraph_shingles(para, k=k)
            if not shingles:
                continue
            if shingles & seen:
                project_keep[idx] = False
            else:
                seen |= shingles

        # Packs: process in reverse order so later packs win.
        pack_names = list(pack_texts.keys())
        pack_keep: Dict[str, List[bool]] = {p: [True] * len(pack_pars[p]) for p in pack_names}

        for pack in reversed(pack_names):
            keep_flags = pack_keep[pack]
            for idx, para in enumerate(pack_pars[pack]):
                shingles = _paragraph_shingles(para, k=k)
                if not shingles:
                    continue
                if shingles & seen:
                    keep_flags[idx] = False
                else:
                    seen |= shingles

        # Core (lowest)
        core_keep: List[bool] = [True] * len(core_pars)
        for idx, para in enumerate(core_pars):
            shingles = _paragraph_shingles(para, k=k)
            if not shingles:
                continue
            if shingles & seen:
                core_keep[idx] = False
            else:
                seen |= shingles

        # Rebuild deduplicated text in layer order: Core → Packs → Project
        dedup_core = "\n\n".join(
            [p for p, keep in zip(core_pars, core_keep) if keep]
        ).strip()

        dedup_packs: Dict[str, str] = {}
        for pack in pack_names:
            pars = pack_pars[pack]
            keep_flags = pack_keep[pack]
            kept = [p for p, keep in zip(pars, keep_flags) if keep]
            dedup_packs[pack] = "\n\n".join(kept).strip()

        dedup_project = "\n\n".join(
            [p for p, keep in zip(project_pars, project_keep) if keep]
        ).strip()

        return dedup_core, dedup_packs, dedup_project

    def compose(
        self,
        name: str,
        packs: List[str],
        *,
        project_overrides: bool = True,
        dry_min_shingles: Optional[int] = None,
    ) -> GuidelineCompositionResult:
        """Compose a single guideline from Core + Packs + Project layers."""
        core = self.core_path(name)
        pack_paths_list = self.pack_paths(name, packs)
        project = self.project_override_path(name) if project_overrides else None

        # When composing TDD, also merge TESTING overlays from packs/project.
        testing_pack_paths: List[Path] = []
        testing_project: Optional[Path] = None
        if name == "TDD":
            testing_pack_paths = self.pack_paths("TESTING", packs)
            if project_overrides:
                testing_project = self.project_override_path("TESTING")

        if core is None and not pack_paths_list and not testing_pack_paths and project is None and testing_project is None:
            raise ComposeError(f"Guideline not found in any layer: {name}")

        pack_paths: Dict[str, List[Path]] = {}
        def _add_pack_paths(paths: List[Path]) -> None:
            for p in paths:
                pack_name = p.parent.parent.name
                pack_paths.setdefault(pack_name, []).append(p)

        _add_pack_paths(pack_paths_list)
        _add_pack_paths(testing_pack_paths)

        # Flatten to a representative path for metadata while keeping texts merged.
        representative_pack_paths: Dict[str, Path] = {
            pack: sorted(paths)[0] for pack, paths in pack_paths.items()
        }

        paths = GuidelinePaths(core=core, packs=representative_pack_paths, project=project or testing_project)

        core_text = self._resolve_layer_text(core)
        pack_texts: Dict[str, str] = {}
        for pack, paths_list in pack_paths.items():
            parts = [self._resolve_layer_text(p) for p in sorted(paths_list)]
            pack_texts[pack] = "\n\n".join([p for p in parts if p]).strip()

        project_parts: List[str] = []
        if project:
            project_parts.append(self._resolve_layer_text(project))
        if testing_project and testing_project != project:
            project_parts.append(self._resolve_layer_text(testing_project))
        project_text = "\n\n".join([p for p in project_parts if p]).strip()

        # Deduplicate paragraphs across layers using 12‑word shingles
        dedup_core, dedup_packs, dedup_project = self._dedupe_layers(
            name=name,
            core_text=core_text,
            pack_texts=pack_texts,
            project_text=project_text,
            k=12,
        )

        # Assemble final text in layer order
        sections: List[str] = []
        if dedup_core:
            sections.append(dedup_core)

        for pack in packs:
            txt = dedup_packs.get(pack, "")
            if txt:
                sections.append(txt)

        if dedup_project:
            sections.append(dedup_project)

        final_text = "\n\n".join(sections).rstrip() + "\n"

        # Duplication report (for CLI and evidence)
        min_s = (
            int(os.environ.get("EDISON_DRY_MIN_SHINGLES", "2"))
            if dry_min_shingles is None
            else dry_min_shingles
        )
        duplicate_report = dry_duplicate_report(
            {
                "core": core_text,
                "packs": "\n\n".join(pack_texts.values()),
                "overlay": project_text,
            },
            min_shingles=min_s,
            k=12,
        )

        return GuidelineCompositionResult(
            name=name,
            text=final_text,
            paths=paths,
            duplicate_report=duplicate_report,
        )


def compose_guideline(name: str, packs: List[str], project_overrides: bool = True) -> str:
    """Convenience wrapper for composing a single guideline as plain text."""
    registry = GuidelineRegistry()
    result = registry.compose(name, packs, project_overrides=project_overrides)
    return result.text


__all__ = [
    "GuidelineRegistry",
    "GuidelineCompositionResult",
    "GuidelinePaths",
    "compose_guideline",
    "ENGINE_VERSION",
]
