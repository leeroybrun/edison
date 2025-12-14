from __future__ import annotations

from pathlib import Path

import yaml

from tests.helpers.paths import get_repo_root


ROOT = get_repo_root()
DATA_DIR = ROOT / "src" / "edison" / "data"
PACKS_DIR = DATA_DIR / "packs"


def test_pack_rules_sourcepaths_exist() -> None:
    """All pack rule registries must point to existing sourcePath files.

    This prevents composition-time failures when packs are synced into projects
    and a moved guideline path is still referenced by rules.
    """

    registries = sorted(PACKS_DIR.glob("*/rules/registry.yml"))
    assert registries, "Expected at least one pack rules registry.yml"

    missing: list[str] = []

    for reg in registries:
        data = yaml.safe_load(reg.read_text(encoding="utf-8")) or {}

        rules = data.get("rules")
        # Some packs may use a dict-based format; others a list.
        if isinstance(rules, dict):
            entries = list(rules.values())
        elif isinstance(rules, list):
            entries = rules
        else:
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            src = entry.get("sourcePath")
            if not src:
                continue

            src_str = str(src)
            file_part = src_str.split("#", 1)[0]
            full = DATA_DIR / file_part
            if not full.exists():
                missing.append(
                    f"{reg.relative_to(ROOT)} -> {src_str} (missing {full.relative_to(ROOT)})"
                )

    assert not missing, "Missing pack rule sourcePath targets:\n" + "\n".join(missing)
