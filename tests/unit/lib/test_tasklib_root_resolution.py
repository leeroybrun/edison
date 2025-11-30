from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from edison.core.utils.paths import PathResolver
from tests.helpers.env_setup import setup_project_root
from tests.helpers.cache_utils import reset_edison_caches

# Repository root for test fixtures
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_resolve_repo_root_respects_agents_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    PathResolver.resolve_project_root() must honor AGENTS_PROJECT_ROOT as the single
    environment override for the repository root.

    This guards against regressions where other project-specific env vars
    (e.g. project_ROOT) influence Edison core resolution.
    """
    # Only AGENTS_PROJECT_ROOT should influence root resolution
    setup_project_root(monkeypatch, tmp_path)
    monkeypatch.delenv("project_ROOT", raising=False)
    monkeypatch.delenv("project_PROJECT_ROOT", raising=False)

    # Provide a minimal git marker so ROOT detection remains valid
    (tmp_path / ".git").mkdir(parents=True, exist_ok=True)

    # Reload PathResolver module to pick up new environment
    importlib.reload(importlib.import_module("edison.core.utils.paths"))

    resolved = PathResolver.resolve_project_root()
    assert resolved == tmp_path
    assert (resolved / ".git").exists()


def test_resolve_repo_root_ignores_project_env_when_agents_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Edison core must not rely on project_ROOT / project_PROJECT_ROOT for root
    resolution. When AGENTS_PROJECT_ROOT is unset, PathResolver should fall back to
    the actual git repository root, not project-specific env overrides.
    """
    # Ensure generic override is absent
    reset_edison_caches()
    monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)

    # Point project_* to an arbitrary temp directory that is NOT the repo root
    project_root = tmp_path / "project-root"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / ".git").mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("project_ROOT", str(project_root))
    monkeypatch.setenv("project_PROJECT_ROOT", str(project_root))

    # Reload PathResolver module to pick up new environment
    importlib.reload(importlib.import_module("edison.core.utils.paths"))

    resolved = PathResolver.resolve_project_root()

    # RED expectation for this fix: root must live inside the Edison repo
    # tree, and MUST NOT equal the project-specific override directory.
    assert resolved != project_root, (
        "PathResolver.resolve_project_root() should ignore project_* overrides and use "
        "the actual repository root instead"
    )

    # Sanity check: resolved path should be somewhere above REPO_ROOT
    assert any(resolved == cand for cand in REPO_ROOT.parents) or resolved == REPO_ROOT, (
        f"Resolved root {resolved} is not within Edison core ancestry starting "
        f"from {REPO_ROOT}"
    )
