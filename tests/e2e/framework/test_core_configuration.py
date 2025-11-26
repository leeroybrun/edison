from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest

# Add Edison core to path so `from edison.core.session import lib as sessionlib` resolves
_THIS_FILE = Path(__file__).resolve()
_CORE_ROOT = None
for _parent in _THIS_FILE.parents:
    candidate = _parent / ".edison" / "core"
    if (candidate / "lib").exists():
        _CORE_ROOT = candidate
        break

if _CORE_ROOT is None:
    _CORE_ROOT = _THIS_FILE.parents[4]

CORE_ROOT = _CORE_ROOT
def _make_repo(tmp_path: Path, name: str = "example-project") -> Path:
    repo = tmp_path / name
    repo.mkdir(parents=True, exist_ok=True)
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    return repo


def _write_project_overlay(repo: Path, filename: str, data: dict) -> None:
    import yaml

    target = repo / ".edison" / "config" / (filename if filename.endswith(".yml") else f"{filename}.yml")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_sessionlib_project_name_falls_back_to_repo_name(tmp_path, monkeypatch):
    """When PROJECT_NAME and config are missing, repo folder name is used."""
    repo = _make_repo(tmp_path, "demo-repo")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    monkeypatch.delenv("PROJECT_NAME", raising=False)

    from edison.core.session import lib as sessionlib

    assert sessionlib._get_project_name() == "demo-repo"


def test_sessionlib_project_name_from_env(tmp_path, monkeypatch):
    """Project name resolves from PROJECT_NAME env var when set."""
    repo = _make_repo(tmp_path, "env-proj")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    monkeypatch.setenv("PROJECT_NAME", "demo-proj")

    from edison.core.session import lib as sessionlib

    assert sessionlib._get_project_name() == "demo-proj"


def test_sessionlib_project_name_from_config(tmp_path, monkeypatch):
    """Project name resolves from project overlay when env is missing."""
    repo = _make_repo(tmp_path, "cfg-proj")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    monkeypatch.delenv("PROJECT_NAME", raising=False)

    _write_project_overlay(repo, "project", {"project": {"name": "cfg-proj"}})

    from edison.core.session import lib as sessionlib

    assert sessionlib._get_project_name() == "cfg-proj"


def test_sessionlib_requires_database_url(tmp_path, monkeypatch):
    """Verify sessionlib fails when DATABASE_URL not set in env or config."""
    repo = _make_repo(tmp_path, "no-db")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from edison.core.session import lib as sessionlib

    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        sessionlib._get_database_url()


def test_sessionlib_get_database_url_from_env(tmp_path, monkeypatch):
    """DATABASE_URL resolves from environment and returns exact value."""
    repo = _make_repo(tmp_path, "db-env")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    monkeypatch.setenv("DATABASE_URL", "sqldb://user:pass@localhost/db")

    from edison.core.session import lib as sessionlib

    assert sessionlib._get_database_url() == "sqldb://user:pass@localhost/db"


def test_worktree_base_uses_project_name(tmp_path, monkeypatch):
    """Verify worktree paths use worktrees.baseDirectory from config (no mocks)."""
    repo = _make_repo(tmp_path, "worktree-proj")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))

    _write_project_overlay(
        repo,
        "worktrees",
        {
            "project": {"name": "test-project"},
            "worktrees": {"baseDirectory": "custom-worktrees"},
        },
    )

    from edison.core.session import lib as sessionlib

    base_dir = sessionlib._get_worktree_base()
    expected = (repo.parent / "custom-worktrees").resolve()
    assert base_dir == expected


def test_worktree_base_defaults_to_project_name(tmp_path, monkeypatch):
    """Worktree base falls back to ../{project}-worktrees when not configured."""
    repo = _make_repo(tmp_path, "my-project")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    monkeypatch.delenv("PROJECT_NAME", raising=False)

    _write_project_overlay(repo, "project", {"project": {"name": "my-project"}})

    from edison.core.session import lib as sessionlib

    base_dir = sessionlib._get_worktree_base()
    expected = (repo.parent / "my-project-worktrees").resolve()
    assert base_dir == expected
