#!/usr/bin/env python3
from __future__ import annotations

"""
Edison Text Utilities

Generic text processing utilities for composition and validation.
Extracted from composition.utils to maintain coherence - generic utilities
should not be in domain-specific modules.

Contains:
  - DRY duplication detection (shingling)
  - Conditional include rendering
  - Text processing helpers
"""

import re
from typing import Dict, Iterable, List, Set, Tuple

# Engine constants
ENGINE_VERSION = "2.5B-1"


def _strip_headings_and_code(text: str) -> str:
    """Remove fenced code blocks and ATX headings to reduce false positives."""
    # Remove code fences
    stripped = re.sub(r"```[\s\S]*?```", "\n", text)
    # Remove headings starting with '#'
    lines = [ln for ln in stripped.splitlines() if not ln.strip().startswith("#")]
    return "\n".join(lines)


def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words."""
    # Lowercase, split on non-word boundaries
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def _shingles(words: List[str], k: int = 12) -> Set[Tuple[str, ...]]:
    """Generate k-word shingles from a list of words."""
    if k <= 0 or len(words) < k:
        return set()
    return {tuple(words[i : i + k]) for i in range(0, len(words) - k + 1)}


def dry_duplicate_report(sections: Dict[str, str], *, min_shingles: int = 2, k: int = 12) -> Dict:
    """Return duplication report between sections using shingled hashes.

    sections keys typically: core, packs (concatenated), overlay
    We enforce DRY primarily between core and packs.
    """
    prepped: Dict[str, Set[Tuple[str, ...]]] = {}
    for name, txt in sections.items():
        tokens = _tokenize(_strip_headings_and_code(txt))
        prepped[name] = _shingles(tokens, k=k)

    core = prepped.get("core", set())
    packs = prepped.get("packs", set())
    overlay = prepped.get("overlay", set())

    core_pack_intersection = core.intersection(packs)
    core_overlay_intersection = core.intersection(overlay)

    violations = []
    if len(core_pack_intersection) >= min_shingles:
        violations.append({
            "pair": ["core", "packs"],
            "shingles": len(core_pack_intersection),
            "threshold": min_shingles,
        })
    if len(core_overlay_intersection) >= min_shingles:
        violations.append({
            "pair": ["core", "overlay"],
            "shingles": len(core_overlay_intersection),
            "threshold": min_shingles,
        })

    return {
        "engineVersion": ENGINE_VERSION,
        "k": k,
        "minShingles": min_shingles,
        "violations": violations,
        "counts": {
            "core": len(core),
            "packs": len(packs),
            "overlay": len(overlay),
        },
    }


_CONDITIONAL_PACK_RE = re.compile(
    r"\{\{\s*include-if:has-pack\(([^)]+)\):(.*?)\}\}",
    flags=re.DOTALL,
)

# Allow Mustache-style pack conditionals used in some validator templates
_CONDITIONAL_PACK_BLOCK_RE = re.compile(
    r"\{\{\s*#if\s+pack:([^}]+)\}\}(.*?)\{\{\s*/if\s*\}\}",
    flags=re.DOTALL,
)

# Normalize bare `{{include path}}` directives to `{{include:path}}`
_INCLUDE_SPACE_RE = re.compile(r"\{\{\s*include\s+([^}:][^}]*)\}\}")


def render_conditional_includes(
    template: str,
    active_packs: Iterable[str],
) -> str:
    """Process ``{{include-if:has-pack(name):...}}`` directives for packs.

    Any directive whose ``name`` is present in ``active_packs`` is replaced by
    its inner content; others are removed entirely. This is deliberately
    conservative so core templates can embed pack‑specific guidance without
    leaking template syntax when a pack is inactive.
    """
    active: Set[str] = {str(p).strip() for p in active_packs if str(p).strip()}
    if not template:
        return template

    def _block_replacer(match: re.Match) -> str:
        pack_name = (match.group(1) or "").strip()
        content = match.group(2) or ""
        if pack_name not in active:
            return ""
        return content

    # Expand Mustache-style pack conditionals first so inner content is preserved
    template = _CONDITIONAL_PACK_BLOCK_RE.sub(_block_replacer, template)

    def _replacer(match: re.Match) -> str:
        pack_name = (match.group(1) or "").strip()
        content = match.group(2) or ""
        if pack_name not in active:
            return ""

        stripped = content.strip()
        if not stripped:
            return ""

        # If the conditional content isn't already an include directive,
        # treat it as a path to include so downstream resolution can expand it.
        if stripped.startswith("{{"):
            return content

        return f"{{{{include:{stripped}}}}}"

    template = _CONDITIONAL_PACK_RE.sub(_replacer, template)

    # Normalize any remaining bare include directives for compatibility
    return _INCLUDE_SPACE_RE.sub(lambda m: f"{{{{include:{(m.group(1) or '').strip()}}}}}", template)


__all__ = [
    "ENGINE_VERSION",
    "dry_duplicate_report",
    "render_conditional_includes",
    "_strip_headings_and_code",
    "_tokenize",
    "_shingles",
]
