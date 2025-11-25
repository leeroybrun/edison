from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest


_cur = Path(__file__).resolve()
CORE_ROOT = None
for parent in _cur.parents:
    if (parent / "lib" / "composition" / "__init__.py").exists():
        CORE_ROOT = parent
        break

assert CORE_ROOT is not None, "cannot locate Edison core lib root"

if str(CORE_ROOT) not in sys.path:

from edison.core.paths import (  # type: ignore  # noqa: E402
    PathResolver,
    EdisonPathError,
    is_git_repository,
    get_git_root,
)


@pytest.fixture(autouse=True)
def _reset_project_root_cache() -> None:
    """Ensure each test observes a fresh project-root cache."""
    import edison.core.paths.resolver as paths  # type: ignore

    paths._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
    yield
    paths._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]


class TestPathResolver:
    def test_resolve_project_root_from_env_var(self, isolated_project_env: Path) -> None:
        """Project root resolves from AGENTS_PROJECT_ROOT when set."""
        root = PathResolver.resolve_project_root()
        assert root == isolated_project_env
        assert (root / ".git").exists()
        assert (root / ".project").exists()

    def test_resolve_project_root_from_git_dir(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When env vars are unset, root is discovered via .git walk."""
        # Remove overrides set by fixture
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("project_ROOT", raising=False)
        monkeypatch.delenv("project_PROJECT_ROOT", raising=False)

        # CWD is already tmp_path from isolated_project_env fixture
        root = PathResolver.resolve_project_root()
        assert root == isolated_project_env
        assert (root / ".git").exists()

    def test_resolve_project_root_fails_on_edison_dir(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Fail fast when root would resolve to .edison directory."""
        edison_root = tmp_path / ".edison"
        edison_root.mkdir(parents=True, exist_ok=True)
        (edison_root / ".git").mkdir()

        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(edison_root))

        with pytest.raises((EdisonPathError, ValueError)):
            PathResolver.resolve_project_root()

    def test_detect_session_id_explicit(self, isolated_project_env: Path) -> None:
        """Explicit session id argument takes precedence."""
        sid = PathResolver.detect_session_id(explicit="sess-123")
        assert sid == "sess-123"

    def test_detect_session_id_from_env(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Session id resolves from project_SESSION environment variable."""
        # Ensure explicit argument would not be used
        monkeypatch.delenv("EDISON_SESSION_ID", raising=False)
        monkeypatch.delenv("project_SESSION_ID", raising=False)

        monkeypatch.setenv("project_SESSION", "env-session-001")

        sid = PathResolver.detect_session_id()
        assert sid == "env-session-001"

    def test_find_evidence_round_latest(self, isolated_project_env: Path) -> None:
        """Latest evidence round is selected when round is None."""
        task_id = "task-123"
        evidence_base = (
            isolated_project_env
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
        )
        (evidence_base / "round-1").mkdir(parents=True, exist_ok=True)
        (evidence_base / "round-2").mkdir(parents=True, exist_ok=True)

        latest = PathResolver.find_evidence_round(task_id)
        assert latest.name == "round-2"

    def test_find_evidence_round_specific(self, isolated_project_env: Path) -> None:
        """Specific evidence round can be requested explicitly."""
        task_id = "task-456"
        evidence_base = (
            isolated_project_env
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
        )
        (evidence_base / "round-1").mkdir(parents=True, exist_ok=True)
        (evidence_base / "round-2").mkdir(parents=True, exist_ok=True)

        round_one = PathResolver.find_evidence_round(task_id, round=1)
        assert round_one.name == "round-1"


class TestGitHelpers:
    def test_is_git_repository_true_for_root(self, isolated_project_env: Path) -> None:
        """is_git_repository reports True for a directory with .git."""
        assert is_git_repository(isolated_project_env) is True

    def test_is_git_repository_false_for_non_git_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """is_git_repository returns False when no .git is present."""
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("project_ROOT", raising=False)
        monkeypatch.delenv("project_PROJECT_ROOT", raising=False)
        root = tmp_path / "no-git-project"
        root.mkdir(parents=True, exist_ok=True)
        assert is_git_repository(root) is False

    def test_get_git_root_from_child_directory(self, isolated_project_env: Path) -> None:
        """get_git_root walks up to the directory containing .git."""
        child = isolated_project_env / "subdir" / "nested"
        child.mkdir(parents=True, exist_ok=True)
        git_root = get_git_root(child)
        assert git_root == isolated_project_env

    def test_get_git_root_none_when_not_in_repo(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """get_git_root returns None outside any git repository."""
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("project_ROOT", raising=False)
        monkeypatch.delenv("project_PROJECT_ROOT", raising=False)
        root = tmp_path / "no-git-project"
        root.mkdir(parents=True, exist_ok=True)
        assert get_git_root(root) is None
