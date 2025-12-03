#!/usr/bin/env python3
from __future__ import annotations

"""
Edison Guideline Composition Engine

Thin wrapper using core LayerDiscovery for discovery.
Guidelines use 'concatenate + dedupe' composition mode (different from section-based).

Features:
  - Discovery via core LayerDiscovery
  - Concatenate composition mode (Core → Packs → Project)
  - DRY enforcement using 12-word shingles (headings/code ignored)

Architecture:
    BaseEntityManager
    └── BaseRegistry
        └── GuidelineRegistry (this module)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

from edison.core.entity import BaseRegistry
from ..includes import resolve_includes, ComposeError
from edison.core.utils.text import (
    dry_duplicate_report,
    ENGINE_VERSION,
    _split_paragraphs,
    _paragraph_shingles,
)

# Import core composition system
from ..core import LayeredComposer, LayerSource


# -----------------------
# Text processing helpers (guideline-specific)
# -----------------------

def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Guideline file not found: {path}")
    return path.read_text(encoding="utf-8")


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


class GuidelineRegistry(BaseRegistry[GuidelineCompositionResult]):
    """Registry for discovering and composing guidelines.
    
    Extends BaseRegistry with guideline-specific functionality:
    - Concatenate + dedupe composition mode
    - DRY enforcement using shingles
    
    Uses core LayerDiscovery for discovery.
    """
    
    entity_type: str = "guideline"

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        super().__init__(repo_root)

        # Core guidelines from bundled data (NOT .edison/core/ - that is legacy)
        self.core_guidelines_dir = self.core_dir / "guidelines"
        # Project guidelines at .edison/guidelines/
        self.project_guidelines_dir = self.project_dir / "guidelines"
        # Pack directories for discovery
        self.bundled_guidelines_packs_dir = self.bundled_packs_dir
        self.project_guidelines_packs_dir = self.project_packs_dir

        # Use core composer for discovery
        self._composer = LayeredComposer(repo_root=self.project_root, content_type="guidelines")
    
    # ------- BaseRegistry Interface Implementation -------
    
    def discover_core(self) -> Dict[str, Path]:
        """Discover core guidelines (returns paths)."""
        result: Dict[str, Path] = {}
        if self.core_guidelines_dir.exists():
            for f in self.core_guidelines_dir.rglob("*.md"):
                if f.is_file() and not f.stem.startswith("_"):
                    result[f.stem] = f
        return result
    
    def discover_packs(self, packs: List[str]) -> Dict[str, Path]:
        """Discover guidelines from bundled AND project packs (returns paths)."""
        result: Dict[str, Path] = {}
        
        # Check both bundled and project packs
        pack_dirs = [self.bundled_guidelines_packs_dir, self.project_guidelines_packs_dir]
        
        for pack in packs:
            for base_dir in pack_dirs:
                pdir = base_dir / pack / "guidelines"
                if not pdir.exists():
                    continue
                for f in pdir.rglob("*.md"):
                    if f.is_file() and not f.stem.startswith("_"):
                        # Project packs override bundled packs
                        result[f.stem] = f
        return result
    
    def discover_project(self) -> Dict[str, Path]:
        """Discover project guidelines (returns paths)."""
        result: Dict[str, Path] = {}
        if self.project_guidelines_dir.exists():
            for f in self.project_guidelines_dir.rglob("*.md"):
                if f.is_file() and not f.stem.startswith("_"):
                    result[f.stem] = f
        return result
    
    def exists(self, name: str) -> bool:
        """Check if a guideline exists in any layer."""
        return (
            self.core_path(name) is not None or
            name in self.discover_project()
        )
    
    def get(self, name: str) -> Optional[Path]:
        """Get the path to a guideline by name.
        
        Returns path from first layer where found (project > packs > core).
        """
        # Check project first
        project_path = self.project_override_path(name)
        if project_path:
            return project_path
        # Check core
        core = self.core_path(name)
        if core:
            return core
        return None
    
    def get_all(self) -> List[str]:
        """Get all guideline names from core layer."""
        return list(self.discover_core().keys())

    # ---------- Discovery ----------
    # Guidelines use 'concatenate' mode - same-name files are merged, not shadowed.
    # This is simpler discovery that allows same-name files across layers.
    
    def core_path(self, name: str) -> Optional[Path]:
        """Find a core guideline (supports nested directories)."""
        if not self.core_guidelines_dir.exists():
            return None
        matches = sorted(self.core_guidelines_dir.rglob(f"{name}.md"))
        return matches[0] if matches else None

    def pack_paths(self, name: str, packs: List[str]) -> List[Path]:
        """Find pack guideline files from bundled AND project packs.
        
        For 'concatenate' mode, same-name files are extensions, not shadows.
        Searches both bundled packs and project packs.
        """
        paths: List[Path] = []
        pack_dirs = [self.bundled_guidelines_packs_dir, self.project_guidelines_packs_dir]
        
        for pack in packs:
            for base_dir in pack_dirs:
                pdir = base_dir / pack / "guidelines"
                if not pdir.exists():
                    continue
                # Find in root or nested subdirectories
                matches = sorted(pdir.rglob(f"{name}.md"))
                paths.extend(matches)
        return paths

    def project_override_path(self, name: str) -> Optional[Path]:
        """Find project guideline overrides (supports nested directories)."""
        if not self.project_guidelines_dir.exists():
            return None
        matches = sorted(self.project_guidelines_dir.rglob(f"{name}.md"))
        return matches[0] if matches else None

    def all_names(self, packs: List[str], *, include_project: bool = True) -> List[str]:
        """Return all guideline names discovered across layers.
        
        Searches bundled core, bundled packs, project packs, and project overrides.
        """
        names: Set[str] = set()

        # Core guidelines (bundled)
        if self.core_guidelines_dir.exists():
            for f in self.core_guidelines_dir.rglob("*.md"):
                if f.is_file() and not f.stem.startswith("_"):
                    names.add(f.stem)

        # Pack guidelines (bundled AND project packs)
        pack_dirs = [self.bundled_guidelines_packs_dir, self.project_guidelines_packs_dir]
        for pack in packs:
            for base_dir in pack_dirs:
                pdir = base_dir / pack / "guidelines"
                if not pdir.exists():
                    continue
                for f in pdir.rglob("*.md"):
                    if f.is_file() and not f.stem.startswith("_"):
                        names.add(f.stem)

        # Project guidelines
        if include_project and self.project_guidelines_dir.exists():
            for f in self.project_guidelines_dir.rglob("*.md"):
                if f.is_file() and not f.stem.startswith("_"):
                    names.add(f.stem)

        return sorted(names)

    def get_subfolder(self, name: str, packs: List[str]) -> Optional[str]:
        """Determine the subfolder for a guideline based on source location."""
        # Check project first
        project_path = self.project_override_path(name)
        if project_path and self.project_guidelines_dir.exists():
            try:
                rel_path = project_path.parent.relative_to(self.project_guidelines_dir)
                return str(rel_path) if str(rel_path) != "." else None
            except ValueError:
                pass
        
        # Check packs (both bundled and project)
        pack_dirs = [self.bundled_guidelines_packs_dir, self.project_guidelines_packs_dir]
        for pack in packs:
            for base_dir in pack_dirs:
                pack_dir = base_dir / pack / "guidelines"
                pack_paths_list = self.pack_paths(name, [pack])
                for p in pack_paths_list:
                    try:
                        rel_path = p.parent.relative_to(pack_dir)
                        return str(rel_path) if str(rel_path) != "." else None
                    except ValueError:
                        pass
        
        # Check core
        core_path = self.core_path(name)
        if core_path and self.core_guidelines_dir.exists():
            try:
                rel_path = core_path.parent.relative_to(self.core_guidelines_dir)
                return str(rel_path) if str(rel_path) != "." else None
            except ValueError:
                pass
        
        return None

    # ---------- Composition (concatenate + dedupe mode) ----------
    
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
        """Deduplicate paragraphs across layers using 12‑word shingles."""
        core_pars = _split_paragraphs(core_text)
        pack_pars: Dict[str, List[str]] = {
            pack: _split_paragraphs(txt) for pack, txt in pack_texts.items()
        }
        project_pars = _split_paragraphs(project_text)

        seen: Set[Tuple[str, ...]] = set()

        # Project (highest priority)
        project_keep: List[bool] = [True] * len(project_pars)
        for idx, para in enumerate(project_pars):
            shingles = _paragraph_shingles(para, k=k)
            if shingles and shingles & seen:
                project_keep[idx] = False
            elif shingles:
                seen |= shingles

        # Packs (reverse order so later packs win)
        pack_names = list(pack_texts.keys())
        pack_keep: Dict[str, List[bool]] = {p: [True] * len(pack_pars[p]) for p in pack_names}

        for pack in reversed(pack_names):
            keep_flags = pack_keep[pack]
            for idx, para in enumerate(pack_pars[pack]):
                shingles = _paragraph_shingles(para, k=k)
                if shingles and shingles & seen:
                    keep_flags[idx] = False
                elif shingles:
                    seen |= shingles

        # Core (lowest priority)
        core_keep: List[bool] = [True] * len(core_pars)
        for idx, para in enumerate(core_pars):
            shingles = _paragraph_shingles(para, k=k)
            if shingles and shingles & seen:
                core_keep[idx] = False
            elif shingles:
                seen |= shingles

        # Rebuild
        dedup_core = "\n\n".join([p for p, keep in zip(core_pars, core_keep) if keep]).strip()
        dedup_packs: Dict[str, str] = {}
        for pack in pack_names:
            pars = pack_pars[pack]
            kept = [p for p, keep in zip(pars, pack_keep[pack]) if keep]
            dedup_packs[pack] = "\n\n".join(kept).strip()
        dedup_project = "\n\n".join([p for p, keep in zip(project_pars, project_keep) if keep]).strip()

        return dedup_core, dedup_packs, dedup_project

    def compose(
        self,
        name: str,
        packs: List[str],
        *,
        project_overrides: bool = True,
        dry_min_shingles: Optional[int] = None,
    ) -> GuidelineCompositionResult:
        """Compose a single guideline using concatenate + dedupe mode."""
        core = self.core_path(name)
        pack_paths_list = self.pack_paths(name, packs)
        project = self.project_override_path(name) if project_overrides else None

        # TDD special case: also merge TESTING overlays
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
                # Structure: packs/{pack}/guidelines/{subfolder}/file.md
                # Navigate up to find the pack name (folder containing "guidelines")
                parent = p.parent
                while parent.name != "guidelines" and parent.parent != parent:
                    parent = parent.parent
                pack_name = parent.parent.name if parent.name == "guidelines" else p.parent.parent.name
                pack_paths.setdefault(pack_name, []).append(p)

        _add_pack_paths(pack_paths_list)
        _add_pack_paths(testing_pack_paths)

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

        # Get config for deduplication
        from edison.core.config import ConfigManager
        cfg = ConfigManager().load_config(validate=False)
        dry_config = cfg.get("composition", {}).get("dryDetection", {})
        k = dry_config.get("shingleSize", 12)

        dedup_core, dedup_packs, dedup_project = self._dedupe_layers(
            name=name,
            core_text=core_text,
            pack_texts=pack_texts,
            project_text=project_text,
            k=k,
        )

        # Assemble final text
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

        # DRY report
        min_s = dry_min_shingles if dry_min_shingles is not None else dry_config.get("minShingles", 2)

        duplicate_report = dry_duplicate_report(
            {"core": core_text, "packs": "\n\n".join(pack_texts.values()), "overlay": project_text},
            min_shingles=min_s,
            k=k,
        )

        return GuidelineCompositionResult(
            name=name,
            text=final_text,
            paths=paths,
            duplicate_report=duplicate_report,
        )


def compose_guideline(name: str, packs: List[str], project_overrides: bool = True) -> str:
    """Convenience wrapper for composing a single guideline."""
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



