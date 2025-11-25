from __future__ import annotations

import yaml
from pathlib import Path


def test_triggers_exist_in_pack_yml():
    root = Path.cwd() / ".edison" / "packs"
    for pdir in root.iterdir():
        if not pdir.is_dir() or pdir.name.startswith("_"):
            continue
        yml = pdir / "pack.yml"
        if not yml.exists():
            # Not a concrete pack (e.g., template); skip
            continue
        data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        triggers = data.get("triggers")
        assert isinstance(triggers, list) and triggers, f"Missing triggers in {pdir.name}"
