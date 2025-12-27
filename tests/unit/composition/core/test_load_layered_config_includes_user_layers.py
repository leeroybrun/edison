from __future__ import annotations

from pathlib import Path

from edison.core.composition.core.base import CompositionBase


def test_load_layered_config_includes_user_and_user_pack_layers(isolated_project_env: Path) -> None:
    """CompositionBase layered YAML loading must include user + user-pack layers."""
    root = isolated_project_env

    # Activate a pack so pack directories are considered.
    project_cfg_dir = root / ".edison" / "config"
    project_cfg_dir.mkdir(parents=True, exist_ok=True)
    (project_cfg_dir / "packs.yaml").write_text("packs:\n  active:\n    - p1\n", encoding="utf-8")

    # User pack layer (~/.edison/packs/<pack>/config/foo.yaml)
    user_pack_cfg = root / ".edison-user" / "packs" / "p1" / "config"
    user_pack_cfg.mkdir(parents=True, exist_ok=True)
    (user_pack_cfg / "foo.yaml").write_text(
        "marker:\n  source: user_pack\n  user_pack: true\n",
        encoding="utf-8",
    )

    # Project pack layer (.edison/packs/<pack>/config/foo.yaml)
    project_pack_cfg = root / ".edison" / "packs" / "p1" / "config"
    project_pack_cfg.mkdir(parents=True, exist_ok=True)
    (project_pack_cfg / "foo.yaml").write_text(
        "marker:\n  source: project_pack\n  project_pack: true\n",
        encoding="utf-8",
    )

    # User layer (~/.edison/config/foo.yaml)
    user_cfg_dir = root / ".edison-user" / "config"
    user_cfg_dir.mkdir(parents=True, exist_ok=True)
    (user_cfg_dir / "foo.yaml").write_text(
        "marker:\n  source: user\n  user: true\n",
        encoding="utf-8",
    )

    # Project layer (.edison/config/foo.yaml)
    (project_cfg_dir / "foo.yaml").write_text(
        "marker:\n  source: project\n  project: true\n",
        encoding="utf-8",
    )

    base = CompositionBase(project_root=root)
    loaded = base._load_layered_config("foo", subdirs=["config"])

    assert loaded["marker"]["user_pack"] is True
    assert loaded["marker"]["project_pack"] is True
    assert loaded["marker"]["user"] is True
    assert loaded["marker"]["project"] is True
    assert loaded["marker"]["source"] == "project"

