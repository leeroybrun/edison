from __future__ import annotations

"""Database configuration should flow through ConfigManager (no direct env lookups)."""

from pathlib import Path

import pytest
import yaml

from edison.core.config import ConfigManager
from edison.core.config.cache import clear_all_caches
from edison.core.session import database, reset_config_cache


def _write_database_defaults(repo_root: Path, *, url: str | None, enabled: bool = True) -> Path:
    """Write database config override to the project config directory."""
    config_path = repo_root / ".edison" / "config" / "database.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write a project config override (not defaults)
    db_cfg = {"enabled": enabled, "url": url}
    config_content = {"database": db_cfg}

    config_path.write_text(yaml.safe_dump(config_content, sort_keys=False), encoding="utf-8")
    return config_path


def test_database_url_from_defaults(isolated_project_env: Path) -> None:
    """ConfigManager exposes database.url from project config when provided."""
    _write_database_defaults(isolated_project_env, url="postgres://defaults/db")
    clear_all_caches()
    reset_config_cache()

    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    db_cfg = cfg.get("database") or {}

    assert db_cfg.get("url") == "postgres://defaults/db"


def test_database_url_env_override(monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path) -> None:
    """EDISON_database__url must override YAML config."""
    _write_database_defaults(isolated_project_env, url="postgres://defaults/db")
    monkeypatch.setenv("EDISON_database__url", "postgres://env/override")
    clear_all_caches()
    reset_config_cache()

    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    db_cfg = cfg.get("database") or {}

    assert db_cfg.get("url") == "postgres://env/override"


def test_database_url_legacy_env_alias(monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path) -> None:
    """DATABASE_URL should act as a legacy alias feeding config database.url."""
    _write_database_defaults(isolated_project_env, url="postgres://defaults/db")
    monkeypatch.setenv("DATABASE_URL", "postgres://legacy/alias")
    clear_all_caches()
    reset_config_cache()

    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    db_cfg = cfg.get("database") or {}

    assert db_cfg.get("url") == "postgres://legacy/alias"


def test_database_url_required_error(monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path) -> None:
    """When database.enabled is true and url missing, an explicit error is raised."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("EDISON_database__url", raising=False)
    _write_database_defaults(isolated_project_env, url=None, enabled=True)
    clear_all_caches()
    reset_config_cache()

    with pytest.raises(ValueError, match="database.url.*EDISON_database__url.*DATABASE_URL"):
        database._get_database_url()


def test_database_module_uses_config_value(monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path) -> None:
    """database._get_database_url should return the value from ConfigManager (no direct env read)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("EDISON_database__url", raising=False)
    _write_database_defaults(isolated_project_env, url="postgres://from-config/db", enabled=True)
    clear_all_caches()
    reset_config_cache()

    assert database._get_database_url() == "postgres://from-config/db"
