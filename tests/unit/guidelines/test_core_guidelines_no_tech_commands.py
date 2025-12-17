from __future__ import annotations

from pathlib import Path

import re

from edison.data import get_data_path


# Core guideline files must be technology-agnostic.
# Packs inject stack-specific commands/examples.
FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bpnpm\b", re.IGNORECASE),
    re.compile(r"\bnpm\b", re.IGNORECASE),
    re.compile(r"\bmypy\b", re.IGNORECASE),
    re.compile(r"\bruff\b", re.IGNORECASE),
    re.compile(r"\bpytest\b", re.IGNORECASE),
    re.compile(r"__tests__", re.IGNORECASE),
]


def _iter_core_guidelines() -> list[Path]:
    root = Path(get_data_path("guidelines"))
    return sorted([p for p in root.rglob("*.md") if p.is_file()])


def test_core_guidelines_contain_no_tech_specific_commands() -> None:
    root = Path(get_data_path("guidelines"))
    offenders: list[str] = []

    for path in _iter_core_guidelines():
        rel = path.relative_to(root)
        content = path.read_text(encoding="utf-8")

        for lineno, line in enumerate(content.splitlines(), start=1):
            for pat in FORBIDDEN_PATTERNS:
                if pat.search(line):
                    offenders.append(f"{rel}:{lineno} - {line.strip()}")
                    break

    assert not offenders, (
        "Core guidelines contain technology-specific commands/examples. "
        "Move these into packs or replace with placeholders/sections.\n"
        + "\n".join(offenders)
    )




