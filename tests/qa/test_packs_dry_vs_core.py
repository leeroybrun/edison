from __future__ import annotations

from pathlib import Path


def _headings(path: Path) -> set[str]:
    hs: set[str] = set()
    if not path.exists():
        return hs
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("## ") or s.startswith("### "):
            hs.add(s.lstrip("# ").strip().lower())
    return hs


def test_packs_do_not_duplicate_core_headings():
    core_dir = Path.cwd() / ".edison/core/validators"
    core_heads: set[str] = set()
    for f in core_dir.rglob("*.md"):
        core_heads |= _headings(f)

    packs_dir = Path.cwd() / ".edison/packs"
    pack_heads: set[str] = set()
    for f in packs_dir.rglob("guidelines/*.md"):
        pack_heads |= _headings(f)

    overlap = core_heads & pack_heads
    assert not overlap, f"Duplicate headings across core and packs: {sorted(overlap)[:10]}"

