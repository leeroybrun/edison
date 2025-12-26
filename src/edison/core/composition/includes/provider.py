"""Composed include provider for TemplateEngine include resolution.

Goal: Resolve {{include:*}} and {{include-section:*}} from the *composed* view of
content (core → packs → project), not raw source files.

This enables include-only fragments (e.g. guidelines/includes/**) to be:
- overlayable/extendable like any other entity
- usable as include targets from any composed artifact (agents/constitutions/etc)

This module is intentionally small and single-purpose. It is used by:
- ComposableRegistry (default, non-materializing provider)
- ComposableTypesManager.write_type (materializing provider that respects path mapping)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Set, Tuple


def merge_extends_preserve_sections(text: str) -> str:
    """Merge EXTEND blocks into SECTION blocks, keeping SECTION markers.

    Some entities (notably include-only guideline fragments) intentionally keep
    SECTION markers so callers can {{include-section:...}} from them. When such
    an entity is composed using "concatenate" mode, EXTEND blocks are not merged
    by the section strategy; we merge them here to keep include-section correct.
    """
    try:
        import re

        from edison.core.composition.core.sections import SectionParser

        parser = SectionParser()
        if not parser.SECTION_PATTERN.search(text):
            return text
        extensions = parser.parse_extensions(text)
        if not extensions:
            return text

        merged = parser.merge_extensions(text, extensions)
        merged = parser.EXTEND_PATTERN.sub("", merged)
        merged = re.sub(r"\n{3,}", "\n\n", merged).strip()
        return merged
    except Exception:
        return text


@dataclass(frozen=True)
class ComposedIncludeProvider:
    """Provider that resolves include paths via composed entities."""

    types_manager: "ComposableTypesManager"  # noqa: F821
    packs: Tuple[str, ...]
    materialize: bool = False
    path_mapper: Optional[Callable[[Path], Path]] = None

    def build(self) -> Callable[[str], Optional[str]]:
        enabled_types = self.types_manager.get_enabled_types()
        # Build content_path → type_name mapping (prefer longest match).
        path_index = sorted(
            ((ct.content_path.strip("/"), ct.name) for ct in enabled_types if ct.content_path),
            key=lambda t: len(t[0]),
            reverse=True,
        )

        cache: Dict[str, str] = {}
        in_progress: Set[str] = set()

        def _strip_quotes(raw: str) -> str:
            raw = raw.strip()
            if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
                return raw[1:-1]
            return raw

        def _match_type(include_path: str) -> Optional[tuple[str, str]]:
            # Returns (type_name, remainder)
            p = include_path.lstrip("/")
            for content_path, type_name in path_index:
                if p == content_path:
                    return type_name, ""
                if p.startswith(content_path + "/"):
                    return type_name, p[len(content_path) + 1 :]
            return None

        def provider(path: str) -> Optional[str]:
            raw = _strip_quotes(path)
            if not raw:
                return None

            cached = cache.get(raw)
            if cached is not None:
                return cached

            if raw in in_progress:
                return f"<!-- ERROR: Circular composed-include detected: {raw} -->"

            match = _match_type(raw)
            if not match:
                return None

            type_name, remainder = match
            if not remainder:
                return None

            entity_name = Path(remainder).with_suffix("").as_posix()

            in_progress.add(raw)
            try:
                registry = self.types_manager.get_registry(type_name)
                if registry is None:
                    return None

                result = registry.compose(entity_name, list(self.packs), include_provider=provider)
                if result is None:
                    return None

                text = self.types_manager._to_string(result)
                cache[raw] = text

                if self.materialize:
                    type_cfg = self.types_manager.get_type(type_name)
                    if type_cfg is not None and type_cfg.output_path:
                        out_dir = self.types_manager._comp_config.resolve_output_path(type_cfg.output_path)
                        out_path = self.types_manager._resolve_file_path(type_cfg, entity_name, out_dir)
                        target = self.path_mapper(out_path) if self.path_mapper else out_path
                        self.types_manager.writer.write_text(target, text)

                return text
            finally:
                in_progress.discard(raw)

        return provider


__all__ = ["ComposedIncludeProvider", "merge_extends_preserve_sections"]







