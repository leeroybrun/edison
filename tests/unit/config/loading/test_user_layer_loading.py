from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.config import ConfigManager
from edison.core.config.cache import clear_all_caches, get_cached_config


@pytest.fixture(autouse=True)
def clear_caches() -> None:
    clear_all_caches()
    yield
    clear_all_caches()


def test_load_pack_configs_user_pack_layer_between_bundled_and_project(tmp_path: Path) -> None:
    """User pack config loads after bundled pack but before project pack."""
    bundled_pack = tmp_path / "bundled_packs" / "test-pack" / "config"
    bundled_pack.mkdir(parents=True)
    (bundled_pack / "custom.yaml").write_text(
        "custom:\n  source: bundled\n  bundled_only: true\n", encoding="utf-8"
    )

    user_pack = tmp_path / "user_packs" / "test-pack" / "config"
    user_pack.mkdir(parents=True)
    (user_pack / "custom.yaml").write_text(
        "custom:\n  source: user\n  user_only: true\n", encoding="utf-8"
    )

    project_pack = tmp_path / "project_packs" / "test-pack" / "config"
    project_pack.mkdir(parents=True)
    (project_pack / "custom.yaml").write_text(
        "custom:\n  source: project\n  project_only: true\n", encoding="utf-8"
    )

    mgr = ConfigManager(tmp_path)
    mgr.bundled_packs_dir = tmp_path / "bundled_packs"
    mgr.user_packs_dir = tmp_path / "user_packs"  # type: ignore[attr-defined]
    mgr.project_packs_dir = tmp_path / "project_packs"

    cfg = mgr._load_pack_configs({}, ["test-pack"])
    assert cfg["custom"]["source"] == "project"
    assert cfg["custom"]["bundled_only"] is True
    assert cfg["custom"]["user_only"] is True
    assert cfg["custom"]["project_only"] is True


def test_load_pack_configs_iterates_all_pack_roots(tmp_path: Path) -> None:
    """_load_pack_configs() should iterate pack roots to support N roots without drift."""
    bundled_pack = tmp_path / "bundled_packs" / "test-pack" / "config"
    bundled_pack.mkdir(parents=True)
    (bundled_pack / "custom.yaml").write_text("custom:\n  source: bundled\n", encoding="utf-8")

    extra_pack = tmp_path / "extra_packs" / "test-pack" / "config"
    extra_pack.mkdir(parents=True)
    (extra_pack / "custom.yaml").write_text("custom:\n  extra_only: true\n", encoding="utf-8")

    mgr = ConfigManager(tmp_path)
    mgr.bundled_packs_dir = tmp_path / "bundled_packs"
    mgr.user_packs_dir = tmp_path / "user_packs"  # type: ignore[attr-defined]
    mgr.project_packs_dir = tmp_path / "project_packs"

    from edison.core.packs.paths import PackRoot

    mgr._pack_roots = (  # type: ignore[attr-defined]
        PackRoot(kind="bundled", path=tmp_path / "bundled_packs"),
        PackRoot(kind="extra", path=tmp_path / "extra_packs"),
        PackRoot(kind="user", path=tmp_path / "user_packs"),
        PackRoot(kind="project", path=tmp_path / "project_packs"),
    )

    cfg = mgr._load_pack_configs({}, ["test-pack"])
    assert cfg["custom"]["extra_only"] is True


def test_user_config_overrides_pack_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """User config layer loads after packs and can override pack settings."""
    # Point user config dir at an isolated location for this test.
    user_dir = tmp_path / ".edison-user"
    monkeypatch.setenv("EDISON_paths__user_config_dir", str(user_dir))

    # Pack config sets feature.enabled=false.
    pack_config = tmp_path / "bundled_packs" / "test-pack" / "config"
    pack_config.mkdir(parents=True)
    (pack_config / "feature.yaml").write_text("feature:\n  enabled: false\n", encoding="utf-8")

    # Project activates pack.
    project_config = tmp_path / ".edison" / "config"
    project_config.mkdir(parents=True)
    (project_config / "packs.yaml").write_text("packs:\n  active:\n    - test-pack\n", encoding="utf-8")

    # User config overrides feature.enabled=true.
    user_cfg_dir = user_dir / "config"
    user_cfg_dir.mkdir(parents=True)
    (user_cfg_dir / "feature.yaml").write_text("feature:\n  enabled: true\n", encoding="utf-8")

    mgr = ConfigManager(tmp_path)
    mgr.bundled_packs_dir = tmp_path / "bundled_packs"

    cfg = mgr.load_config(validate=False, include_packs=True)
    assert cfg["feature"]["enabled"] is True


def test_project_local_config_overrides_project_config(tmp_path: Path) -> None:
    """Project-local config (uncommitted) loads after project config."""
    project_cfg_dir = tmp_path / ".edison" / "config"
    project_cfg_dir.mkdir(parents=True)
    (project_cfg_dir / "custom.yaml").write_text("custom:\n  value: project\n", encoding="utf-8")

    local_cfg_dir = tmp_path / ".edison" / "config.local"
    local_cfg_dir.mkdir(parents=True)
    (local_cfg_dir / "custom.yaml").write_text("custom:\n  value: local\n", encoding="utf-8")

    mgr = ConfigManager(tmp_path)
    cfg = mgr.load_config(validate=False, include_packs=False)
    assert cfg["custom"]["value"] == "local"


def test_project_local_config_can_enable_packs(tmp_path: Path) -> None:
    """Bootstrap packs.active includes project-local config so users can enable packs per-project."""
    # Pack config sets a marker.
    pack_config = tmp_path / "bundled_packs" / "test-pack" / "config"
    pack_config.mkdir(parents=True)
    (pack_config / "marker.yaml").write_text("marker:\n  from_pack: true\n", encoding="utf-8")

    # Project-local activates the pack (without touching committed config).
    local_cfg_dir = tmp_path / ".edison" / "config.local"
    local_cfg_dir.mkdir(parents=True)
    (local_cfg_dir / "packs.yaml").write_text("packs:\n  active:\n    - test-pack\n", encoding="utf-8")

    mgr = ConfigManager(tmp_path)
    mgr.bundled_packs_dir = tmp_path / "bundled_packs"

    cfg = mgr.load_config(validate=False, include_packs=True)
    assert cfg.get("marker", {}).get("from_pack") is True


def test_config_cache_includes_user_config_fingerprint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Changing user config should change the config cache key (no stale reads)."""
    user_dir = tmp_path / ".edison-user"
    monkeypatch.setenv("EDISON_paths__user_config_dir", str(user_dir))

    # First load: no user config.
    cfg1 = get_cached_config(tmp_path, validate=False, include_packs=False)
    assert cfg1.get("user_marker") is None

    # Write a user config file.
    user_cfg_dir = user_dir / "config"
    user_cfg_dir.mkdir(parents=True)
    (user_cfg_dir / "user.yaml").write_text("user_marker: true\n", encoding="utf-8")

    cfg2 = get_cached_config(tmp_path, validate=False, include_packs=False)
    assert cfg2.get("user_marker") is True


def test_user_only_pack_portability_warns_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """When a pack is only available in the user packs dir, Edison warns by default."""
    user_dir = tmp_path / ".edison-user"
    monkeypatch.setenv("EDISON_paths__user_config_dir", str(user_dir))

    # Create pack only in user packs directory.
    (user_dir / "packs" / "private-pack" / "config").mkdir(parents=True)

    # Activate pack in project config.
    project_config = tmp_path / ".edison" / "config"
    project_config.mkdir(parents=True)
    (project_config / "packs.yaml").write_text("packs:\n  active:\n    - private-pack\n", encoding="utf-8")

    caplog.set_level("WARNING")
    mgr = ConfigManager(tmp_path)
    mgr.load_config(validate=False, include_packs=True)

    assert "private-pack" in caplog.text
    assert "user packs directory" in caplog.text.lower()


def test_user_only_pack_portability_can_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Projects can fail-closed when packs resolve only from the user layer."""
    user_dir = tmp_path / ".edison-user"
    monkeypatch.setenv("EDISON_paths__user_config_dir", str(user_dir))

    # Create pack only in user packs directory.
    (user_dir / "packs" / "private-pack" / "config").mkdir(parents=True)

    # Activate pack + require portability enforcement.
    project_config = tmp_path / ".edison" / "config"
    project_config.mkdir(parents=True)
    (project_config / "packs.yaml").write_text(
        "packs:\n"
        "  active:\n"
        "    - private-pack\n"
        "  portability:\n"
        "    userOnly: error\n",
        encoding="utf-8",
    )

    mgr = ConfigManager(tmp_path)
    with pytest.raises(RuntimeError) as excinfo:
        mgr.load_config(validate=False, include_packs=True)
    assert "private-pack" in str(excinfo.value)


def test_missing_pack_portability_warns_by_default(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Missing packs in packs.active warn by default (opt-in error for CI)."""
    project_config = tmp_path / ".edison" / "config"
    project_config.mkdir(parents=True)
    (project_config / "packs.yaml").write_text("packs:\n  active:\n    - missing-pack\n", encoding="utf-8")

    caplog.set_level("WARNING")
    mgr = ConfigManager(tmp_path)
    mgr.load_config(validate=False, include_packs=True)
    assert "missing-pack" in caplog.text
    assert "not found" in caplog.text.lower()


def test_missing_pack_portability_can_error(tmp_path: Path) -> None:
    """Missing packs can fail-closed when packs.portability.missing=error."""
    project_config = tmp_path / ".edison" / "config"
    project_config.mkdir(parents=True)
    (project_config / "packs.yaml").write_text(
        "packs:\n"
        "  active:\n"
        "    - missing-pack\n"
        "  portability:\n"
        "    missing: error\n",
        encoding="utf-8",
    )

    mgr = ConfigManager(tmp_path)
    with pytest.raises(RuntimeError) as excinfo:
        mgr.load_config(validate=False, include_packs=True)
    assert "missing-pack" in str(excinfo.value)
