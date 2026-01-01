from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest

from tests.helpers.paths import get_repo_root
from tests.helpers.io_utils import write_yaml
from tests.helpers.env_setup import setup_project_root
from tests.helpers.fixtures import create_repo_with_git

# Add Edison core to path so test helpers can resolve
_THIS_FILE = Path(__file__).resolve()
_CORE_ROOT = None
for _parent in _THIS_FILE.parents:
    candidate = _parent / ".edison" / "core"
    if (candidate / "lib").exists():
        _CORE_ROOT = candidate
        break

if _CORE_ROOT is None:
    _CORE_ROOT = get_repo_root()

CORE_ROOT = _CORE_ROOT
def _make_repo(tmp_path: Path, name: str = "example-project") -> Path:
    """Create a test repository with git initialized."""
    return create_repo_with_git(tmp_path, name=name)




def test_sessionlib_project_name_falls_back_to_repo_name(tmp_path, monkeypatch):
    """When PROJECT_NAME and config are missing, repo folder name is used."""
    repo = _make_repo(tmp_path, "demo-repo")
    monkeypatch.chdir(repo)
    setup_project_root(monkeypatch, repo)
    monkeypatch.delenv("PROJECT_NAME", raising=False)

    from tests.helpers import session as sessionlib

    assert sessionlib._get_project_name() == "demo-repo"


def test_sessionlib_project_name_from_env(tmp_path, monkeypatch):
    """Project name resolves from PROJECT_NAME env var when set."""
    repo = _make_repo(tmp_path, "env-proj")
    monkeypatch.chdir(repo)
    setup_project_root(monkeypatch, repo)
    monkeypatch.setenv("PROJECT_NAME", "demo-proj")

    from tests.helpers import session as sessionlib

    assert sessionlib._get_project_name() == "demo-proj"


def test_sessionlib_project_name_from_config(tmp_path, monkeypatch):
    """Project name resolves from project overlay when env is missing."""
    repo = _make_repo(tmp_path, "cfg-proj")
    monkeypatch.chdir(repo)
    setup_project_root(monkeypatch, repo)
    monkeypatch.delenv("PROJECT_NAME", raising=False)

    write_yaml(repo / ".edison" / "config" / "project.yml", {"project": {"name": "cfg-proj"}})

    from tests.helpers import session as sessionlib

    assert sessionlib._get_project_name() == "cfg-proj"


def test_sessionlib_requires_database_url(tmp_path, monkeypatch):
    """Verify sessionlib fails when DATABASE_URL not set in env or config."""
    repo = _make_repo(tmp_path, "no-db")
    monkeypatch.chdir(repo)
    setup_project_root(monkeypatch, repo)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from tests.helpers import session as sessionlib

    with pytest.raises(ValueError, match="database.url.*EDISON_database__url.*DATABASE_URL"):
        sessionlib._get_database_url()


def test_sessionlib_get_database_url_from_env(tmp_path, monkeypatch):
    """DATABASE_URL resolves from environment and returns exact value."""
    repo = _make_repo(tmp_path, "db-env")
    monkeypatch.chdir(repo)
    setup_project_root(monkeypatch, repo)
    monkeypatch.setenv("DATABASE_URL", "sqldb://user:pass@localhost/db")

    from tests.helpers import session as sessionlib

    assert sessionlib._get_database_url() == "sqldb://user:pass@localhost/db"


def test_worktree_base_uses_project_name(tmp_path, monkeypatch):
    """Verify worktree paths use worktrees.baseDirectory from config (no mocks)."""
    repo = _make_repo(tmp_path, "worktree-proj")
    monkeypatch.chdir(repo)
    setup_project_root(monkeypatch, repo)

    write_yaml(
        repo / ".edison" / "config" / "worktrees.yml",
        {
            "project": {"name": "test-project"},
            "worktrees": {"baseDirectory": "custom-worktrees"},
        },
    )

    from tests.helpers import session as sessionlib

    base_dir = sessionlib._get_worktree_base()
    # Relative worktree paths that do NOT start with '..' are anchored inside the repo.
    expected = (repo / "custom-worktrees").resolve()
    assert base_dir == expected


def test_worktree_base_defaults_to_project_name(tmp_path, monkeypatch):
    """Worktree base defaults to in-repo `.worktrees/` when not configured."""
    repo = _make_repo(tmp_path, "my-project")
    monkeypatch.chdir(repo)
    setup_project_root(monkeypatch, repo)
    monkeypatch.delenv("PROJECT_NAME", raising=False)

    write_yaml(repo / ".edison" / "config" / "project.yml", {"project": {"name": "my-project"}})

    from tests.helpers import session as sessionlib

    base_dir = sessionlib._get_worktree_base()
    expected = (repo / ".worktrees").resolve()
    assert base_dir == expected
