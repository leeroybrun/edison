from __future__ import annotations

import re
from pathlib import Path


BANNED = re.compile(r"\b(project|app)\b", re.IGNORECASE)


def iter_pack_files():
    root = Path.cwd() / ".edison" / "packs"
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".md", ".yml", ".yaml", ".ts", ".tsx", ".json", ".css"}:
            yield p


def test_no_banned_terms_in_packs():
    offenders = []
    for f in iter_pack_files():
        text = f.read_text(encoding="utf-8", errors="ignore")
        if BANNED.search(text):
            offenders.append(str(f))
    assert not offenders, f"Banned terms found in: {offenders}"
