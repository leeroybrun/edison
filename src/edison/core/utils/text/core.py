#!/usr/bin/env python3
"""Core text processing utilities.

Generic text processing utilities for composition and validation.
Contains:
  - DRY duplication detection (shingling)
  - Conditional include rendering
  - Text processing helpers
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Set, Tuple


_ENGINE_VERSION_CACHE: str | None = None


def get_engine_version() -> str:
    """Load text processing engine version from configuration.

    Returns:
        str: The engine version identifier

    Raises:
        RuntimeError: If config cannot be loaded or engine version is missing
    """
    global _ENGINE_VERSION_CACHE
    if _ENGINE_VERSION_CACHE is not None:
        return _ENGINE_VERSION_CACHE

    try:
        from edison.core.config import ConfigManager
        from edison.core.utils.paths import resolve_project_root

        repo_root = resolve_project_root()
        cfg_manager = ConfigManager(repo_root)
        full_config = cfg_manager.load_config(validate=False)

        if "text_processing" not in full_config:
            raise RuntimeError(
                "text_processing configuration section is missing. "
                "Add 'text_processing' section to your YAML config."
            )

        engine_version = full_config["text_processing"].get("engine_version")
        if not engine_version:
            raise RuntimeError(
                "text_processing.engine_version is not configured. "
                "Add 'text_processing.engine_version' to your YAML config."
            )

        _ENGINE_VERSION_CACHE = str(engine_version)
        return _ENGINE_VERSION_CACHE
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(
            f"Failed to load text processing engine version: {e}"
        ) from e


# Lazy property for backward compatibility - accessed via function
class _EngineVersionDescriptor:
    """Descriptor that lazily loads ENGINE_VERSION on first access."""

    def __get__(self, obj, objtype=None) -> str:
        return get_engine_version()


class _EngineVersionModule:
    """Module-level lazy accessor for ENGINE_VERSION."""
    ENGINE_VERSION = _EngineVersionDescriptor()


# For backward compat, expose as module-level variable that's lazily evaluated
# Usage: from edison.core.utils.text.core import ENGINE_VERSION
# Will call get_engine_version() on first actual use
def __getattr__(name: str):
    if name == "ENGINE_VERSION":
        return get_engine_version()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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


def _split_paragraphs(text: str) -> List[str]:
    """Split text into logical paragraphs separated by blank lines."""
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
    """Compute k-word shingles for a paragraph, ignoring headings/code."""
    cleaned = _strip_headings_and_code(paragraph)
    tokens = _tokenize(cleaned)
    return _shingles(tokens, k=k)


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
        "engineVersion": get_engine_version(),
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
    conservative so core templates can embed pack-specific guidance without
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
    "get_engine_version",
    "dry_duplicate_report",
    "render_conditional_includes",
    "_strip_headings_and_code",
    "_tokenize",
    "_shingles",
    "_split_paragraphs",
    "_paragraph_shingles",
]
