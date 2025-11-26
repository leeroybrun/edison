from __future__ import annotations

import itertools
import difflib
from pathlib import Path

from edison.data import get_data_path, read_yaml


def _normalize(text: str) -> str:
    """Strip trailing whitespace to make similarity comparisons stable."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(lines)


def test_no_duplicate_api_docs():
    cfg = read_yaml("config", "pack_content_rules.yaml")["pack_api_docs"]
    packs_dir = get_data_path("packs")

    pack_dirs = [
        p
        for p in packs_dir.iterdir()
        if p.is_dir() and not any(p.name.startswith(prefix) for prefix in cfg.get("skip_packs_prefixes", []))
    ]

    duplicates_within_pack = []
    api_docs = {}

    for pack_dir in pack_dirs:
        api_paths: list[Path] = []
        for subdir in cfg.get("subdirectories", []):
            api_paths.extend(sorted((pack_dir / subdir).glob(cfg["filename"])))

        if len(api_paths) > cfg.get("max_per_pack", 1):
            duplicates_within_pack.append((pack_dir.name, [p.relative_to(packs_dir) for p in api_paths]))

        if api_paths:
            api_docs[pack_dir.name] = api_paths[0].resolve()

    assert not duplicates_within_pack, f"Duplicate api.md files found within packs: {duplicates_within_pack}"

    normalized = {name: _normalize(path.read_text(encoding="utf-8")) for name, path in api_docs.items()}
    threshold = float(cfg["similarity_threshold"])

    cross_pack_duplicates = []
    for (name_a, content_a), (name_b, content_b) in itertools.combinations(normalized.items(), 2):
        if api_docs[name_a] == api_docs[name_b]:
            continue  # Shared canonical file is allowed; no duplicated source.

        ratio = difflib.SequenceMatcher(None, content_a, content_b).ratio()
        if ratio >= threshold:
            cross_pack_duplicates.append((name_a, name_b, round(ratio, 3)))

    assert not cross_pack_duplicates, f"Duplicate api.md content across packs: {cross_pack_duplicates}"
