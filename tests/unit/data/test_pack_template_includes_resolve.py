from __future__ import annotations

import re
from pathlib import Path

from tests.helpers.paths import get_repo_root


ROOT = get_repo_root()
DATA_DIR = ROOT / "src" / "edison" / "data"
PACKS_DIR = DATA_DIR / "packs"


_INCLUDE_RE = re.compile(r"\{\{\s*include(?:-optional)?\s*:\s*([^}]+)\}\}")
_INCLUDE_SECTION_RE = re.compile(r"\{\{\s*include-section\s*:\s*([^#}]+)#([^}]+)\}\}")


def _read(rel_path: str) -> str:
    return (DATA_DIR / rel_path).read_text(encoding="utf-8")


def _has_section(text: str, section: str) -> bool:
    start = f"<!-- section: {section} -->"
    end = f"<!-- /section: {section} -->"
    return start in text and end in text


def test_pack_template_includes_resolve() -> None:
    """All {{include:*}} and {{include-section:*}} paths in packs must resolve.

    This prevents silent prompt truncation when an include target is missing,
    and ensures include-section targets have the referenced section markers.
    """

    md_files = sorted(PACKS_DIR.rglob("*.md"))
    assert md_files, "Expected markdown files under packs/"

    missing: list[str] = []
    missing_sections: list[str] = []

    for path in md_files:
        text = path.read_text(encoding="utf-8")

        for include_target in _INCLUDE_RE.findall(text):
            target = include_target.strip()
            # Only validate includes that target the data tree (avoid external placeholders)
            if not (target.startswith("packs/") or target.startswith("guidelines/") or target.startswith("constitutions/")):
                continue

            full = DATA_DIR / target
            if not full.exists():
                missing.append(f"{path.relative_to(ROOT)} -> {{include:{target}}} (missing {full.relative_to(ROOT)})")

        for include_path, section in _INCLUDE_SECTION_RE.findall(text):
            inc_path = include_path.strip()
            section = section.strip()

            if not (inc_path.startswith("packs/") or inc_path.startswith("guidelines/") or inc_path.startswith("constitutions/")):
                continue

            full = DATA_DIR / inc_path
            if not full.exists():
                missing.append(
                    f"{path.relative_to(ROOT)} -> {{include-section:{inc_path}#{section}}} (missing {full.relative_to(ROOT)})"
                )
                continue

            included_text = full.read_text(encoding="utf-8")
            if not _has_section(included_text, section):
                missing_sections.append(
                    f"{path.relative_to(ROOT)} -> {full.relative_to(ROOT)} missing section '{section}'"
                )

    assert not missing, "Unresolved include targets:\n" + "\n".join(missing)
    assert not missing_sections, "Unresolved include-section markers:\n" + "\n".join(missing_sections)
