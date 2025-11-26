from __future__ import annotations

"""Database configuration should flow through ConfigManager (no direct env lookups)."""

from pathlib import Path

import pytest
import yaml

from edison.core.config import ConfigManager
from edison.core.session import database
from edison.core.session.config import SessionConfig


def _write_database_defaults(repo_root: Path, *, url: str | None, enabled: bool = True) -> Path:
    """Ensure defaults.yaml under the isolated repo has a database section with url."""
    defaults_path = repo_root / ".edison" / "core" / "config" / "defaults.yaml"
    defaults_path.parent.mkdir(parents=True, exist_ok=True)

    current = yaml.safe_load(defaults_path.read_text()) if defaults_path.exists() else {}
    if current is None:
        current = {}

    current.setdefault("project", {"name": "database-tests"})
    db_cfg = current.get("database") or {}
    db_cfg.update({"enabled": enabled, "url": url})
    current["database"] = db_cfg

    defaults_path.write_text(yaml.safe_dump(current, sort_keys=False), encoding="utf-8")
    return defaults_path


def test_database_url_from_defaults(isolated_project_env: Path) -> None:
    """ConfigManager exposes database.url from defaults.yaml when provided."""
    _write_database_defaults(isolated_project_env, url="postgres://defaults/db")

    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    db_cfg = cfg.get("database") or {}

    assert db_cfg.get("url") == "postgres://defaults/db"


def test_database_url_env_override(monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path) -> None:
    """EDISON_database__url must override YAML defaults."""
    _write_database_defaults(isolated_project_env, url="postgres://defaults/db")
    monkeypatch.setenv("EDISON_database__url", "postgres://env/override")

    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    db_cfg = cfg.get("database") or {}

    assert db_cfg.get("url") == "postgres://env/override"


def test_database_url_legacy_env_alias(monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path) -> None:
    """DATABASE_URL should act as a legacy alias feeding config database.url."""
    _write_database_defaults(isolated_project_env, url="postgres://defaults/db")
    monkeypatch.setenv("DATABASE_URL", "postgres://legacy/alias")

    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    db_cfg = cfg.get("database") or {}

    assert db_cfg.get("url") == "postgres://legacy/alias"


def test_database_url_required_error(monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path) -> None:
    """When database.enabled is true and url missing, an explicit error is raised."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("EDISON_database__url", raising=False)
    _write_database_defaults(isolated_project_env, url=None, enabled=True)

    database._CONFIG = SessionConfig(repo_root=isolated_project_env)

    with pytest.raises(ValueError, match="database.url.*EDISON_database__url.*DATABASE_URL"):
        database._get_database_url()


def test_database_module_uses_config_value(monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path) -> None:
    """database._get_database_url should return the value from ConfigManager (no direct env read)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("EDISON_database__url", raising=False)
    _write_database_defaults(isolated_project_env, url="postgres://from-config/db", enabled=True)

    database._CONFIG = SessionConfig(repo_root=isolated_project_env)

    assert database._get_database_url() == "postgres://from-config/db"
