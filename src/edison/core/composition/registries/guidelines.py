#!/usr/bin/env python3
"""Edison Guideline Registry.

Thin wrapper around ComposableRegistry for guideline composition.
Guidelines use concatenate + dedupe mode (different from section-based).

Architecture:
    CompositionBase → ComposableRegistry → GuidelineRegistry
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Set

from edison.core.entity.composable_registry import ComposableRegistry
from edison.core.utils.text import (
    dry_duplicate_report,
    ENGINE_VERSION,
)


@dataclass
class GuidelinePaths:
    """Paths to guideline sources across layers."""
    core: Optional[Path]
    packs: Dict[str, Path]  # pack name → path
    project: Optional[Path]


@dataclass
class GuidelineCompositionResult:
    """Result of guideline composition."""
    name: str
    text: str
    paths: GuidelinePaths
    duplicate_report: Dict[str, Any]


class GuidelineRegistry(ComposableRegistry[GuidelineCompositionResult]):
    """Registry for discovering and composing guidelines.

    Extends ComposableRegistry with:
    - Concatenate + dedupe composition mode
    - DRY enforcement using shingles

    Guidelines use `enable_dedupe=True` to remove duplicate content.
    """

    content_type: ClassVar[str] = "guidelines"
    file_pattern: ClassVar[str] = "*.md"
    strategy_config: ClassVar[Dict[str, Any]] = {
        "enable_sections": False,  # Guidelines use concatenate, not sections
        "enable_dedupe": True,     # Enable DRY deduplication
        "dedupe_shingle_size": 12,
        "enable_template_processing": True,
    }

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        """Initialize guideline registry."""
        # Accept repo_root for backward compatibility
        super().__init__(project_root=repo_root)

    # ------- Discovery Helpers -------

    def core_path(self, name: str) -> Optional[Path]:
        """Find a core guideline path."""
        core_entities = self.discover_core()
        return core_entities.get(name)

    def pack_paths(self, name: str, packs: List[str]) -> List[Path]:
        """Find pack guideline files from all active packs."""
        paths: List[Path] = []
        for pack in packs:
            pack_dir = self.bundled_packs_dir / pack / self.content_type
            if pack_dir.exists():
                matches = sorted(pack_dir.rglob(f"{name}.md"))
                paths.extend(matches)
            # Also check project packs
            proj_pack_dir = self.project_packs_dir / pack / self.content_type
            if proj_pack_dir.exists():
                matches = sorted(proj_pack_dir.rglob(f"{name}.md"))
                paths.extend(matches)
        return paths

    def project_override_path(self, name: str) -> Optional[Path]:
        """Find project guideline override."""
        guidelines_dir = self.project_dir / self.content_type
        if guidelines_dir.exists():
            matches = sorted(guidelines_dir.rglob(f"{name}.md"))
            if matches:
                return matches[0]
        return None

    def discover_project(self) -> Dict[str, Path]:
        """Discover project guidelines (returns paths).

        Override base class to avoid shadowing validation.
        Guidelines use concatenate mode - same-name files are extensions, not shadows.
        """
        result: Dict[str, Path] = {}
        guidelines_dir = self.project_dir / self.content_type
        if guidelines_dir.exists():
            for f in guidelines_dir.rglob("*.md"):
                if f.is_file() and not f.stem.startswith("_"):
                    result[f.stem] = f
        return result

    def all_names(self, packs: List[str], *, include_project: bool = True) -> List[str]:
        """Return all guideline names discovered across layers."""
        names: Set[str] = set()

        # Core guidelines
        names.update(self.discover_core().keys())

        # Pack guidelines
        names.update(self.discover_packs(packs).keys())

        # Project guidelines
        if include_project:
            names.update(self.discover_project().keys())

        return sorted(names)

    def get_subfolder(self, name: str, packs: List[str]) -> Optional[str]:
        """Determine the subfolder for a guideline based on source location."""
        # Check project first
        project_path = self.project_override_path(name)
        if project_path:
            guidelines_dir = self.project_dir / self.content_type
            if guidelines_dir.exists():
                try:
                    rel_path = project_path.parent.relative_to(guidelines_dir)
                    return str(rel_path) if str(rel_path) != "." else None
                except ValueError:
                    pass

        # Check packs
        pack_paths_list = self.pack_paths(name, packs)
        for p in pack_paths_list:
            for pack in packs:
                pack_dir = self.bundled_packs_dir / pack / self.content_type
                try:
                    rel_path = p.parent.relative_to(pack_dir)
                    return str(rel_path) if str(rel_path) != "." else None
                except ValueError:
                    pass

        # Check core
        core_path = self.core_path(name)
        if core_path:
            core_dir = self.core_dir / self.content_type
            if core_dir.exists():
                try:
                    rel_path = core_path.parent.relative_to(core_dir)
                    return str(rel_path) if str(rel_path) != "." else None
                except ValueError:
                    pass

        return None

    # ------- Layer Gathering (Override) -------

    def _gather_layers(
        self,
        name: str,
        packs: List[str],
    ) -> List["LayerContent"]:
        """Gather content from all layers for a guideline.

        Guidelines use concatenate mode:
        - Project files at .edison/guidelines/{name}.md (NOT overlays/)
        - Pack files at .edison/packs/{pack}/guidelines/{name}.md
        - Core files from bundled data

        All same-name files are concatenated (not shadowed).
        """
        from edison.core.composition.strategies import LayerContent
        from ..includes import resolve_includes

        layers: List[LayerContent] = []

        # Helper to read and resolve includes
        def read_layer(path: Path, source: str) -> Optional[LayerContent]:
            if path and path.exists():
                try:
                    raw = path.read_text(encoding="utf-8")
                    expanded, _ = resolve_includes(raw, path)
                    return LayerContent(content=expanded, source=source, path=path)
                except Exception:
                    pass
            return None

        # Core layer
        core = self.core_path(name)
        if core:
            layer = read_layer(core, "core")
            if layer:
                layers.append(layer)

        # Pack layers (both bundled and project packs)
        for pack in packs:
            for p in self.pack_paths(name, [pack]):
                layer = read_layer(p, f"pack:{pack}")
                if layer:
                    layers.append(layer)

        # Project layer (direct file, not in overlays/)
        # Check _include_project flag (set by compose())
        include_project = getattr(self, "_include_project", True)
        if include_project:
            project = self.project_override_path(name)
            if project:
                layer = read_layer(project, "project")
                if layer:
                    layers.append(layer)

        return layers

    # ------- Composition -------

    def _post_compose(self, name: str, content: str) -> GuidelineCompositionResult:
        """Transform composed content into GuidelineCompositionResult."""
        packs = self.get_active_packs()

        # Gather paths for result
        core_path = self.core_path(name)
        pack_paths_dict: Dict[str, Path] = {}
        for pack in packs:
            paths = self.pack_paths(name, [pack])
            if paths:
                pack_paths_dict[pack] = paths[0]
        project_path = self.project_override_path(name)

        paths = GuidelinePaths(
            core=core_path,
            packs=pack_paths_dict,
            project=project_path,
        )

        # Generate DRY report
        # Gather text from each layer for report
        core_text = ""
        if core_path and core_path.exists():
            core_text = core_path.read_text(encoding="utf-8")

        packs_text = ""
        for pack in packs:
            for p in self.pack_paths(name, [pack]):
                if p.exists():
                    packs_text += "\n\n" + p.read_text(encoding="utf-8")

        project_text = ""
        if project_path and project_path.exists():
            project_text = project_path.read_text(encoding="utf-8")

        # Get shingle size from config
        cfg = self.config.get("composition", {}) or {}
        dry_cfg = cfg.get("dryDetection", {}) or {}
        min_shingles = dry_cfg.get("minShingles", 2)
        k = dry_cfg.get("shingleSize", 12)

        duplicate_report = dry_duplicate_report(
            {"core": core_text, "packs": packs_text.strip(), "overlay": project_text},
            min_shingles=min_shingles,
            k=k,
        )

        return GuidelineCompositionResult(
            name=name,
            text=content,
            paths=paths,
            duplicate_report=duplicate_report,
        )

    def compose(
        self,
        name: str,
        packs: Optional[List[str]] = None,
        *,
        project_overrides: bool = True,
        dry_min_shingles: Optional[int] = None,
    ) -> GuidelineCompositionResult:
        """Compose a single guideline.

        Args:
            name: Guideline name
            packs: List of active packs
            project_overrides: Whether to include project layer
            dry_min_shingles: Override for DRY detection threshold
        """
        # Store project_overrides flag for _gather_layers
        self._include_project = project_overrides

        try:
            result = super().compose(name, packs)
        finally:
            # Reset flag
            self._include_project = True

        if result is None:
            from ..includes import ComposeError
            raise ComposeError(f"Guideline not found in any layer: {name}")
        return result


def compose_guideline(
    name: str,
    packs: List[str],
    project_overrides: bool = True,
) -> str:
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
