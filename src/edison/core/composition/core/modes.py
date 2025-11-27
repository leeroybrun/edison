"""Composition modes for different content types.

This module defines the composition modes that determine how content
is composed across layers (Core → Packs → Project):

- SECTION: Section-based composition using HTML comment markers
  Used for: agents, validators, constitutions
  
- CONCATENATE: Paragraph-based composition with deduplication
  Used for: guidelines
  
- YAML_MERGE: YAML-based merging by key
  Used for: rules
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from edison.core.utils.text import (
    _split_paragraphs,
    _paragraph_shingles,
)

if TYPE_CHECKING:
    from .sections import SectionComposer


class CompositionMode(Enum):
    """Mode for content composition across layers."""
    
    SECTION = "section"           # Section-based (HTML comments)
    CONCATENATE = "concatenate"   # Paragraph concatenation + dedupe
    YAML_MERGE = "yaml_merge"     # YAML-based merging


# Default composition mode
DEFAULT_MODE = CompositionMode.SECTION


def get_mode(mode_str: Optional[str]) -> CompositionMode:
    """Parse string to CompositionMode, returning DEFAULT_MODE for None/unknown."""
    if mode_str is None:
        return DEFAULT_MODE
    
    mode_str_lower = mode_str.lower().strip()
    
    for mode in CompositionMode:
        if mode.value == mode_str_lower:
            return mode
    
    return DEFAULT_MODE


# ---------------------------------------------------------------------------
# ConcatenateComposer - Guideline-style composition
# ---------------------------------------------------------------------------


@dataclass
class ConcatenateComposer:
    """Composer for concatenate + dedupe mode (guidelines).
    
    Merges content from Core → Packs → Project layers,
    deduplicating paragraphs using shingle-based detection.
    
    Priority order (higher wins for deduplication):
    1. Project (highest priority - keeps content)
    2. Packs (in order - later packs win)
    3. Core (lowest priority - duplicates removed first)
    """
    
    shingle_size: int = 12
    min_shingles: int = 3
    
    @classmethod
    def from_config(cls, config: Optional[Dict] = None) -> "ConcatenateComposer":
        """Create ConcatenateComposer from configuration.
        
        Reads from composition.dryDetection in config.
        Falls back to defaults if not specified.
        
        Args:
            config: Configuration dict. If None, loads from ConfigManager.
            
        Returns:
            Configured ConcatenateComposer instance.
        """
        if config is None:
            from edison.core.config import ConfigManager
            config = ConfigManager().load_config(validate=False)
        
        dry_config = (config.get("composition", {}) or {}).get("dryDetection", {}) or {}
        
        return cls(
            shingle_size=dry_config.get("shingleSize", 12),
            min_shingles=dry_config.get("minShingles", 3),
        )
    
    def compose(
        self,
        core_text: str,
        pack_texts: Dict[str, str],
        project_text: str,
    ) -> str:
        """Compose content from all layers with deduplication.
        
        Args:
            core_text: Content from core layer
            pack_texts: Dict mapping pack name to content
            project_text: Content from project layer
            
        Returns:
            Composed and deduplicated content
        """
        # Parse all layers into paragraphs
        core_pars = _split_paragraphs(core_text)
        pack_pars: Dict[str, List[str]] = {
            pack: _split_paragraphs(txt) for pack, txt in pack_texts.items()
        }
        project_pars = _split_paragraphs(project_text)
        
        # Deduplicate using shingles
        dedup_core, dedup_packs, dedup_project = self._dedupe_layers(
            core_pars=core_pars,
            pack_pars=pack_pars,
            project_pars=project_pars,
        )
        
        # Assemble final text: Core → Packs (in order) → Project
        sections: List[str] = []
        
        if dedup_core:
            sections.append(dedup_core)
        
        for pack in pack_texts.keys():
            txt = dedup_packs.get(pack, "")
            if txt:
                sections.append(txt)
        
        if dedup_project:
            sections.append(dedup_project)
        
        return "\n\n".join(sections).rstrip() + "\n"
    
    def _dedupe_layers(
        self,
        *,
        core_pars: List[str],
        pack_pars: Dict[str, List[str]],
        project_pars: List[str],
    ) -> Tuple[str, Dict[str, str], str]:
        """Deduplicate paragraphs across layers using shingles.
        
        Priority: Project > Packs (reverse order) > Core
        """
        k = self.shingle_size
        seen: Set[Tuple[str, ...]] = set()
        
        # 1. Project (highest priority - process first to "claim" shingles)
        project_keep: List[bool] = [True] * len(project_pars)
        for idx, para in enumerate(project_pars):
            shingles = _paragraph_shingles(para, k=k)
            if shingles and shingles & seen:
                project_keep[idx] = False
            elif shingles:
                seen |= shingles
        
        # 2. Packs (reverse order so later packs win)
        pack_names = list(pack_pars.keys())
        pack_keep: Dict[str, List[bool]] = {
            p: [True] * len(pack_pars[p]) for p in pack_names
        }
        
        for pack in reversed(pack_names):
            keep_flags = pack_keep[pack]
            for idx, para in enumerate(pack_pars[pack]):
                shingles = _paragraph_shingles(para, k=k)
                if shingles and shingles & seen:
                    keep_flags[idx] = False
                elif shingles:
                    seen |= shingles
        
        # 3. Core (lowest priority)
        core_keep: List[bool] = [True] * len(core_pars)
        for idx, para in enumerate(core_pars):
            shingles = _paragraph_shingles(para, k=k)
            if shingles and shingles & seen:
                core_keep[idx] = False
            elif shingles:
                seen |= shingles
        
        # Rebuild texts from kept paragraphs
        dedup_core = "\n\n".join(
            p for p, keep in zip(core_pars, core_keep) if keep
        ).strip()
        
        dedup_packs: Dict[str, str] = {}
        for pack in pack_names:
            pars = pack_pars[pack]
            kept = [p for p, keep in zip(pars, pack_keep[pack]) if keep]
            dedup_packs[pack] = "\n\n".join(kept).strip()
        
        dedup_project = "\n\n".join(
            p for p, keep in zip(project_pars, project_keep) if keep
        ).strip()
        
        return dedup_core, dedup_packs, dedup_project


# ---------------------------------------------------------------------------
# Composer Factory
# ---------------------------------------------------------------------------

def get_composer(mode: CompositionMode, config: Optional[Dict] = None):
    """Get the appropriate composer for a composition mode.
    
    Args:
        mode: The composition mode
        config: Optional config dict for composer initialization
        
    Returns:
        Composer instance for the mode
    """
    if mode == CompositionMode.SECTION:
        from .sections import SectionComposer
        return SectionComposer()
    
    if mode == CompositionMode.CONCATENATE:
        return ConcatenateComposer.from_config(config)
    
    if mode == CompositionMode.YAML_MERGE:
        # YAML merge doesn't use a composer class
        # It's handled directly in the registry
        raise ValueError("YAML_MERGE mode does not use a composer")
    
    # Default to section composer
    from .sections import SectionComposer
    return SectionComposer()


__all__ = [
    "CompositionMode",
    "DEFAULT_MODE",
    "get_mode",
    "ConcatenateComposer",
    "get_composer",
]



