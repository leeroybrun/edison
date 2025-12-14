from __future__ import annotations

from pathlib import Path

import yaml


# Locate repository root
_cur = Path(__file__).resolve()
ROOT = None
for i in range(1, 10):
    if i >= len(_cur.parents):
        break
    cand = _cur.parents[i]
    if (cand / ".git").exists():
        ROOT = cand
        break
assert ROOT is not None, "cannot locate repository root (.git)"

PACKS_DIR = ROOT / "src/edison/data/packs"


def _iter_pack_dirs() -> list[Path]:
    return [p for p in sorted(PACKS_DIR.iterdir()) if p.is_dir() and not p.name.startswith("_")]


def test_pack_manifests_do_not_list_guidelines_to_prevent_drift():
    """Guidelines should be wired via overlays/rules, not duplicated in pack.yml."""
    offenders: list[str] = []

    for pack_dir in _iter_pack_dirs():
        pack_yml = pack_dir / "pack.yml"
        data = yaml.safe_load(pack_yml.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            continue

        if "guidelines" in data:
            offenders.append(f"{pack_dir.name}: pack.yml has top-level 'guidelines'")

        provides = data.get("provides")
        if isinstance(provides, dict) and "guidelines" in provides:
            offenders.append(f"{pack_dir.name}: pack.yml has provides.guidelines")

    assert not offenders, "Pack manifests should not list guidelines:\n" + "\n".join(offenders)


def test_pack_guidelines_only_exist_under_includes():
    offenders: list[str] = []

    for pack_dir in _iter_pack_dirs():
        guidelines_dir = pack_dir / "guidelines"
        if not guidelines_dir.exists():
            continue

        for md in guidelines_dir.rglob("*.md"):
            rel = md.relative_to(pack_dir)
            # Only allow include-only guidelines (single source of truth)
            if rel.parts[:2] != ("guidelines", "includes"):
                offenders.append(f"{pack_dir.name}: {rel}")

    assert not offenders, (
        "Pack guideline markdown must live under guidelines/includes (remove drift-prone docs):\n"
        + "\n".join(offenders)
    )


def test_all_pack_guideline_includes_are_referenced():
    """Every include-only guideline must be referenced by an overlay include-section or a rules registry sourcePath."""
    offenders: list[str] = []

    # Preload all overlay contents once
    overlay_texts: dict[str, str] = {}
    for pack_dir in _iter_pack_dirs():
        parts: list[str] = []
        for md in (pack_dir / "agents").rglob("*.md") if (pack_dir / "agents").exists() else []:
            parts.append(md.read_text(encoding="utf-8"))
        for md in (pack_dir / "validators").rglob("*.md") if (pack_dir / "validators").exists() else []:
            parts.append(md.read_text(encoding="utf-8"))
        overlay_texts[pack_dir.name] = "\n".join(parts)

    # Preload rules registries text
    rules_texts: dict[str, str] = {}
    for pack_dir in _iter_pack_dirs():
        reg = pack_dir / "rules" / "registry.yml"
        rules_texts[pack_dir.name] = reg.read_text(encoding="utf-8") if reg.exists() else ""

    for pack_dir in _iter_pack_dirs():
        pack_name = pack_dir.name
        includes_dir = pack_dir / "guidelines" / "includes"
        if not includes_dir.exists():
            continue

        combined = overlay_texts.get(pack_name, "") + "\n" + rules_texts.get(pack_name, "")

        for md in includes_dir.rglob("*.md"):
            # include-section uses packs/<pack>/... paths
            rel_from_pack_root = md.relative_to(pack_dir).as_posix()
            expected_ref = f"packs/{pack_name}/{rel_from_pack_root}"
            if expected_ref not in combined:
                offenders.append(f"{pack_name}: {rel_from_pack_root} (not referenced)")

    assert not offenders, (
        "Unreferenced include-only pack guideline files (dead content):\n" + "\n".join(offenders)
    )
