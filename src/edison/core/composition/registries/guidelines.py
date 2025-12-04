#!/usr/bin/env python3
"""Edison Guideline Registry (unified).

Uses ComposableRegistry with MarkdownCompositionStrategy (sections disabled,
dedupe enabled). All discovery is handled by LayerDiscovery; this class only
configures strategy and post-processing (duplicate report, paths metadata).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Set

from .base import ComposableRegistry
# Import unified CompositionContext from central location
from edison.core.composition.context import CompositionContext
from edison.core.utils.text import dry_duplicate_report, ENGINE_VERSION


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
    merge_same_name: ClassVar[bool] = True

    def __init__(self, project_root: Optional[Path] = None) -> None:
        super().__init__(project_root=project_root)

    def core_path(self, name: str) -> Optional[Path]:
        return self.discover_core().get(name)

    def compose(
        self,
        name: str,
        packs: Optional[List[str]] = None,
        *,
        project_overrides: bool = True,
        dry_min_shingles: Optional[int] = None,
    ) -> GuidelineCompositionResult:
        """Compose a single guideline by concatenating all same-name layers."""
        packs = packs or self.get_active_packs()

        layers = self._gather_layers(name, packs)
        if not project_overrides:
            layers = [l for l in layers if l.source != "project"]

        if not layers:
            from ..includes import ComposeError
            raise ComposeError(f"Guideline not found in any layer: {name}")

        context = CompositionContext(
            active_packs=packs,
            config=self.config,
            project_root=self.project_root,
        )
        composed = self.strategy.compose(layers, context)

        # Paths metadata
        core_path = next((l.path for l in layers if l.source == "core"), None)
        pack_paths: Dict[str, Path] = {}
        for l in layers:
            if l.source.startswith("pack:") and l.path:
                pack = l.source.split(":", 1)[1]
                pack_paths.setdefault(pack, l.path)
        project_path = next((l.path for l in layers if l.source == "project"), None)
        paths = GuidelinePaths(core=core_path, packs=pack_paths, project=project_path)

        # DRY report
        cfg = self.config.get("composition", {}) or {}
        dry_cfg = cfg.get("dryDetection", {}) or {}
        min_shingles = dry_cfg.get("minShingles", 2)
        k = dry_cfg.get("shingleSize", 12)

        core_text = next((l.content for l in layers if l.source == "core"), "")
        packs_text = "\n\n".join(l.content for l in layers if l.source.startswith("pack:"))
        project_text = next((l.content for l in layers if l.source == "project"), "")

        duplicate_report = dry_duplicate_report(
            {"core": core_text, "packs": packs_text.strip(), "overlay": project_text},
            min_shingles=min_shingles,
            k=k,
        )

        return GuidelineCompositionResult(
            name=name,
            text=composed,
            paths=paths,
            duplicate_report=duplicate_report,
        )

    def all_names(self, packs: List[str], *, include_project: bool = True) -> List[str]:
        names = set(self.discover_core().keys())
        names.update(self.discover_packs(packs).keys())
        if include_project:
            proj_dir = self.project_dir / self.content_type
            if proj_dir.exists():
                for f in proj_dir.glob("*.md"):
                    if f.is_file() and not f.stem.startswith("_"):
                        names.add(f.stem)
        return sorted(names)


def compose_guideline(
    name: str,
    packs: List[str],
    project_overrides: bool = True,
    *,
    project_root: Optional[Path] = None,
) -> str:
    """Convenience wrapper for composing a single guideline."""
    registry = GuidelineRegistry(project_root=project_root)
    result = registry.compose(name, packs, project_overrides=project_overrides)
    return result.text


__all__ = [
    "GuidelineRegistry",
    "GuidelineCompositionResult",
    "GuidelinePaths",
    "compose_guideline",
    "ENGINE_VERSION",
]
