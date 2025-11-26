from __future__ import annotations

from importlib import reload
from pathlib import Path

import pytest
import yaml

from edison.core.config import ConfigManager


def _write_overlay(root: Path, name: str, data: dict) -> Path:
    """Write a project overlay YAML file under .edison/config."""
    path = root / ".edison" / "config" / f"{name}.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_project_metadata_defaults_present(isolated_project_env: Path) -> None:
    """ConfigManager should expose project metadata defaults from defaults.yaml."""
    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    project = cfg.get("project") or {}

    assert project.get("name") == "project"
    assert project.get("owner") is None
    assert project.get("audit_terms") == []


def test_project_metadata_env_overrides_defaults(monkeypatch, isolated_project_env: Path) -> None:
    """EDISON_* env vars must override YAML project defaults."""
    base_cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    base_project = base_cfg.get("project") or {}

    # Defaults must be present before overrides are applied
    assert base_project.get("name") == "project"
    assert base_project.get("owner") is None
    assert base_project.get("audit_terms") == []

    monkeypatch.setenv("EDISON_project__name", "env-proj")
    monkeypatch.setenv("EDISON_project__owner", "env-owner")
    monkeypatch.setenv("EDISON_project__audit_terms", "[\"alpha\", \"beta\"]")

    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    project = cfg.get("project") or {}

    assert project.get("name") == "env-proj"
    assert project.get("owner") == "env-owner"
    assert project.get("audit_terms") == ["alpha", "beta"]


def test_worktree_path_uses_project_name_from_config(monkeypatch, isolated_project_env: Path) -> None:
    """Worktree target paths must substitute project.name in templates."""
    _write_overlay(
        isolated_project_env,
        "project",
        {"project": {"name": "demo-proj"}},
    )
    _write_overlay(
        isolated_project_env,
        "worktrees",
        {"worktrees": {"baseDirectory": "../{PROJECT_NAME}-custom"}},
    )

    from edison.core.session import worktree
    from edison.core.session.config import SessionConfig

    # Ensure module uses fresh config bound to isolated repo
    worktree._CONFIG = SessionConfig(repo_root=isolated_project_env)

    target, branch = worktree.resolve_worktree_target("sess-123")

    expected_base = (isolated_project_env.parent / "demo-proj-custom" / "sess-123").resolve()
    assert target == expected_base
    assert branch == "session/sess-123"


def test_purity_uses_project_terms_from_config(isolated_project_env: Path) -> None:
    """Purity checks should honor project.name and project.audit_terms from config."""
    _write_overlay(
        isolated_project_env,
        "project",
        {"project": {"name": "Acme-App", "audit_terms": ["acme term"]}},
    )

    guideline = isolated_project_env / ".edison" / "core" / "guidelines" / "core.md"
    guideline.parent.mkdir(parents=True, exist_ok=True)
    guideline.write_text("This mentions acme app and acme term\n", encoding="utf-8")

    from edison.core.composition.audit import purity
    from edison.core.composition.audit.guideline_discovery import GuidelineRecord

    rec = GuidelineRecord(path=guideline, category="core")
    violations = purity.purity_violations([rec])
    terms = [hit["term"] for hit in violations["core_project_terms"]]

    assert "acme app" in terms
    assert "acme term" in terms


def test_default_owner_prefers_config_owner(monkeypatch, isolated_project_env: Path) -> None:
    """default_owner should use configured project.owner before process detection."""
    _write_overlay(
        isolated_project_env,
        "project",
        {"project": {"name": "owner-proj", "owner": "config-owner"}},
    )

    from edison.core.task import io as task_io

    reload(task_io)

    owner = task_io.default_owner(process_finder=lambda: ("detected-owner", 9999))
    assert owner == "config-owner"
