from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from edison.cli.debug.resolve import main


def test_debug_resolve_outputs_layer_sources(tmp_path: Path, capsys) -> None:
    """edison debug resolve prints the exact layer sources in order (JSON)."""
    # Minimal project config enabling a pack.
    cfg_dir = tmp_path / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "packs.yaml").write_text("packs:\n  active:\n    - p1\n", encoding="utf-8")

    # Create a project pack overlay for an existing core guideline.
    pack_overlay = tmp_path / ".edison" / "packs" / "p1" / "guidelines" / "overlays" / "shared"
    pack_overlay.mkdir(parents=True, exist_ok=True)
    (pack_overlay / "VALIDATION.md").write_text("Pack overlay line\n", encoding="utf-8")

    # User overlay.
    user_overlay = tmp_path / ".edison-user" / "guidelines" / "overlays" / "shared"
    user_overlay.mkdir(parents=True, exist_ok=True)
    (user_overlay / "VALIDATION.md").write_text("User overlay line\n", encoding="utf-8")

    # Project overlay.
    project_overlay = tmp_path / ".edison" / "guidelines" / "overlays" / "shared"
    project_overlay.mkdir(parents=True, exist_ok=True)
    (project_overlay / "VALIDATION.md").write_text("Project overlay line\n", encoding="utf-8")

    args = Namespace(
        type="guidelines",
        name="shared/VALIDATION",
        packs=None,
        json=True,
        repo_root=str(tmp_path),
    )
    assert main(args) == 0

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["type"] == "guidelines"
    assert payload["name"] == "shared/VALIDATION"

    applied = payload["applied_layers"]
    assert any(i["origin"] == "core" for i in applied)
    assert any(i.get("pack") == "p1" and i.get("pack_root") == "project" for i in applied)
    assert any(i["origin"] == "user" for i in applied)
    assert any(i["origin"] == "project" for i in applied)

