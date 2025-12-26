"""Ensure pack overlays only EXTEND sections that exist in the base template.

Overlay composition uses `extend:` blocks that attach to `section:` blocks.
If an overlay extends a section that is not defined in the base entity, the
extension is silently dropped (no insertion point).
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.helpers.paths import get_repo_root


ROOT = get_repo_root()
DATA_DIR = ROOT / "src" / "edison" / "data"
PACKS_DIR = DATA_DIR / "packs"


_EXTEND_RE = re.compile(r"<!--\s*extend:\s*([\w.-]+)\s*-->")


def _find_base_entity(pack: str, entity_type: str, name: str) -> Path | None:
    """Find the base entity file for an overlay (core or pack-new)."""
    if entity_type == "agents":
        core_path = DATA_DIR / "agents" / f"{name}.md"
        if core_path.exists():
            return core_path
        pack_new = PACKS_DIR / pack / "agents" / f"{name}.md"
        if pack_new.exists():
            return pack_new
        return None

    if entity_type == "validators":
        # Core validators are nested (global/, critical/, etc.)
        core_matches = list((DATA_DIR / "validators").rglob(f"{name}.md"))
        if core_matches:
            # Prefer deterministic path ordering
            return sorted(core_matches)[0]
        pack_new = PACKS_DIR / pack / "validators" / f"{name}.md"
        if pack_new.exists():
            return pack_new
        return None

    return None


def _base_section_names(base_text: str) -> set[str]:
    """Return SECTION names as authored in the base template.

    Section names are effectively case-sensitive in composition because EXTEND
    keys must match the SECTION key exactly to be inserted.
    """
    from edison.core.composition.core.sections import SectionMode, SectionParser

    parser = SectionParser()
    return {s.name for s in parser.parse(base_text) if s.mode == SectionMode.SECTION}


def test_pack_overlays_only_extend_existing_sections() -> None:
    overlays = sorted(PACKS_DIR.rglob("overlays/*.md"))
    assert overlays, "No pack overlay files found"

    violations: list[str] = []

    for overlay_path in overlays:
        # Expected layout: packs/<pack>/<type>/overlays/<name>.md
        try:
            pack = overlay_path.parts[overlay_path.parts.index("packs") + 1]
            entity_type = overlay_path.parts[overlay_path.parts.index(pack) + 1]
        except Exception:
            continue

        if entity_type not in {"agents", "validators"}:
            continue

        overlay_text = overlay_path.read_text(encoding="utf-8")
        extend_targets = _EXTEND_RE.findall(overlay_text)
        if not extend_targets:
            continue

        entity_name = overlay_path.stem
        base_path = _find_base_entity(pack, entity_type, entity_name)
        if base_path is None:
            violations.append(
                f"{overlay_path.relative_to(ROOT)}: overlay references missing base {entity_type} '{entity_name}'"
            )
            continue

        base_text = base_path.read_text(encoding="utf-8")
        base_sections = _base_section_names(base_text)
        for target in extend_targets:
            if target not in base_sections:
                violations.append(
                    f"{overlay_path.relative_to(ROOT)}: extend '{target}' not found in base {base_path.relative_to(ROOT)}"
                )

    assert not violations, "Invalid overlay EXTEND targets:\n" + "\n".join(violations)










