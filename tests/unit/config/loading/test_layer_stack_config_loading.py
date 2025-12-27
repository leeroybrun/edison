from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.config import ConfigManager
import os
from edison.core.config.cache import get_cached_config


def test_company_layer_config_is_loaded_between_packs_and_user(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = isolated_project_env

    # Isolate user dir (autouse fixture already sets, but keep explicit for clarity)
    user_dir = Path(os.environ["EDISON_paths__user_config_dir"])

    company_dir = root / "company-layer"
    (company_dir / "config").mkdir(parents=True)
    (company_dir / "config" / "company.yaml").write_text("company_marker: true\n", encoding="utf-8")

    # Insert company layer before user via project config/layers.yaml.
    proj_cfg = root / ".edison" / "config"
    proj_cfg.mkdir(parents=True, exist_ok=True)
    (proj_cfg / "layers.yaml").write_text(
        "layers:\n"
        "  roots:\n"
        "    - id: mycompany\n"
        f"      path: {company_dir.as_posix()}\n"
        "      before: user\n",
        encoding="utf-8",
    )

    # Also write a user config marker (higher precedence than company)
    (user_dir / "config").mkdir(parents=True, exist_ok=True)
    (user_dir / "config" / "user.yaml").write_text("user_marker: true\n", encoding="utf-8")

    cfg = ConfigManager(root).load_config(validate=False, include_packs=False)
    assert cfg.get("company_marker") is True
    assert cfg.get("user_marker") is True


def test_company_layer_can_provide_pack_config(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    company_dir = root / "company-layer"
    (company_dir / "config").mkdir(parents=True)

    # Company provides a pack with config.
    pack_cfg = company_dir / "packs" / "company-pack" / "config"
    pack_cfg.mkdir(parents=True, exist_ok=True)
    (pack_cfg / "marker.yaml").write_text("marker:\n  from_company_pack: true\n", encoding="utf-8")

    proj_cfg = root / ".edison" / "config"
    proj_cfg.mkdir(parents=True, exist_ok=True)
    (proj_cfg / "layers.yaml").write_text(
        "layers:\n"
        "  roots:\n"
        "    - id: mycompany\n"
        f"      path: {company_dir.as_posix()}\n"
        "      before: user\n",
        encoding="utf-8",
    )
    (proj_cfg / "packs.yaml").write_text("packs:\n  active:\n    - company-pack\n", encoding="utf-8")

    cfg = ConfigManager(root).load_config(validate=False, include_packs=True)
    assert cfg.get("marker", {}).get("from_company_pack") is True


def test_config_cache_fingerprint_includes_company_layer_config(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    company_dir = root / "company-layer"
    (company_dir / "config").mkdir(parents=True)

    proj_cfg = root / ".edison" / "config"
    proj_cfg.mkdir(parents=True, exist_ok=True)
    (proj_cfg / "layers.yaml").write_text(
        "layers:\n"
        "  roots:\n"
        "    - id: mycompany\n"
        f"      path: {company_dir.as_posix()}\n"
        "      before: user\n",
        encoding="utf-8",
    )

    cfg1 = get_cached_config(root, validate=False, include_packs=False)
    assert cfg1.get("company_marker") is None

    (company_dir / "config" / "company.yaml").write_text("company_marker: true\n", encoding="utf-8")

    cfg2 = get_cached_config(root, validate=False, include_packs=False)
    assert cfg2.get("company_marker") is True
