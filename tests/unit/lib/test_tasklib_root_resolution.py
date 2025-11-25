from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def _core_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "lib" / "task" / "__init__.py").exists() or (
            parent / "lib" / "composition" / "__init__.py"
        ).exists():
            return parent
    raise AssertionError("cannot locate Edison core lib root")


def _ensure_core_on_path() -> Path:
    core_root = _core_root()
    if str(core_root) not in sys.path:
    return core_root


def test_resolve_repo_root_respects_agents_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    _resolve_repo_root must honor AGENTS_PROJECT_ROOT as the single
    environment override for the repository root.

    This guards against regressions where other project-specific env vars
    (e.g. project_ROOT) influence Edison core resolution.
    """
    _ensure_core_on_path()

    # Only AGENTS_PROJECT_ROOT should influence root resolution
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("project_ROOT", raising=False)
    monkeypatch.delenv("project_PROJECT_ROOT", raising=False)

    # Provide a minimal git marker so ROOT detection remains valid
    (tmp_path / ".git").mkdir(parents=True, exist_ok=True)

    task_paths = importlib.reload(importlib.import_module("lib.task.paths"))  # type: ignore[assignment]

    resolved = task_paths._resolve_repo_root()  # type: ignore[attr-defined]
    assert resolved == tmp_path
    assert (resolved / ".git").exists()


def test_resolve_repo_root_ignores_project_env_when_agents_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Edison core must not rely on project_ROOT / project_PROJECT_ROOT for root
    resolution. When AGENTS_PROJECT_ROOT is unset, task should fall back to
    the actual git repository root, not project-specific env overrides.
    """
    core_root = _ensure_core_on_path()

    # Ensure generic override is absent
    monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)

    # Point project_* to an arbitrary temp directory that is NOT the repo root
    project_root = tmp_path / "project-root"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / ".git").mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("project_ROOT", str(project_root))
    monkeypatch.setenv("project_PROJECT_ROOT", str(project_root))

    # Reload task so _resolve_repo_root observes the new env
    task_paths = importlib.reload(importlib.import_module("lib.task.paths"))  # type: ignore[assignment]

    resolved = task_paths._resolve_repo_root()  # type: ignore[attr-defined]

    # RED expectation for this fix: root must live inside the Edison repo
    # tree, and MUST NOT equal the project-specific override directory.
    assert resolved != project_root, (
        "_resolve_repo_root should ignore project_* overrides and use "
        "the actual repository root instead"
    )

    # Sanity check: resolved path should be somewhere above core_root
    assert any(resolved == cand for cand in core_root.parents), (
        f"Resolved root {resolved} is not within Edison core ancestry starting "
        f"from {core_root}"
    )
