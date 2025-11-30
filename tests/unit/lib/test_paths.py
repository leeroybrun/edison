from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


# Repository root for test fixtures
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

from edison.core.utils.paths import (  # type: ignore  # noqa: E402
    EdisonPathError,
    PathResolver,
    resolve_project_root,
)
from edison.core.utils.subprocess import run_with_timeout  # type: ignore  # noqa: E402
from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.env_setup import setup_project_root


@pytest.fixture(autouse=True)
def _reset_project_root_cache() -> None:
    """
    Ensure each test runs with a clean project-root cache so that env/CWD
    manipulations are observed independently.
    """
    reset_edison_caches()
    yield
    reset_edison_caches()


class TestCanonicalProjectRoot:
    def project_dir_is_under_repo_root_not_edison(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        ``.project/`` must live under the real project root, never under
        the ``.edison`` checkout directory even when CWD is inside it.
        """
        # Create a fake Edison core layout inside the isolated repo root
        edison_core = isolated_project_env / ".edison" / "core"
        edison_core.mkdir(parents=True, exist_ok=True)

        # Simulate running from inside .edison/core/*
        monkeypatch.chdir(edison_core)

        root = PathResolver.resolve_project_root()
        assert root == isolated_project_env

        project_dir = PathResolver.get_project_path()
        assert project_dir == (root / ".project").resolve()
        # Ensure we did not accidentally anchor under .edison
        assert ".edison" not in project_dir.parts, ".project must not be rooted under .edison"

    def test_resolve_project_root_never_returns_edison_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Guard rail: resolve_project_root must never resolve to a ``.edison``
        directory, even when the environment explicitly points at one.
        """
        edison_root = tmp_path / ".edison"
        edison_root.mkdir(parents=True, exist_ok=True)

        # Point AGENTS_PROJECT_ROOT at the .edison directory directly
        setup_project_root(monkeypatch, edison_root)

        with pytest.raises(EdisonPathError):
            PathResolver.resolve_project_root()


class TestEnvOverridesAndErrors:
    def test_agents_project_root_env_override_wins(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        When AGENTS_PROJECT_ROOT points at a valid repo root, it must take
        precedence over any other mechanism.
        """
        repo = tmp_path / "project"
        repo.mkdir(parents=True, exist_ok=True)
        (repo / ".git").mkdir()
        (repo / ".project").mkdir()

        setup_project_root(monkeypatch, repo)
        # Even if project-specific env vars are set, they must be ignored
        monkeypatch.setenv("project_ROOT", str(tmp_path / "project-root"))
        monkeypatch.setenv("project_PROJECT_ROOT", str(tmp_path / "project-project-root"))

        root = resolve_project_root()
        assert root == repo

    def test_invalid_agents_project_root_raises_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AGENTS_PROJECT_ROOT pointing at a non-existent path must fail fast."""
        bogus = tmp_path / "does-not-exist"
        setup_project_root(monkeypatch, bogus)

        with pytest.raises(EdisonPathError):
            resolve_project_root()

    def test_project_env_vars_are_ignored_for_root_resolution(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        project_ROOT and project_PROJECT_ROOT must not participate in project
        root resolution; only AGENTS_PROJECT_ROOT and git are canonical.
        """
        # Ensure generic override is absent so fallback must use git
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)

        # Prepare a real git repo that should be treated as the project root
        repo = tmp_path / "real-repo"
        repo.mkdir(parents=True, exist_ok=True)
        run_with_timeout(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)

        # Point project env vars at an unrelated directory that also looks git-y
        project_root = tmp_path / "project-root"
        project_root.mkdir(parents=True, exist_ok=True)
        run_with_timeout(["git", "init"], cwd=project_root, check=True, stdout=subprocess.DEVNULL)

        monkeypatch.setenv("project_ROOT", str(project_root))
        monkeypatch.setenv("project_PROJECT_ROOT", str(project_root))
        monkeypatch.chdir(repo)

        root = resolve_project_root()
        assert root == repo
        assert root != project_root


class TestGitRootDetection:
    def test_git_root_detection_succeeds_in_real_repo(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Git-backed root detection must work in a real git repo."""
        repo = tmp_path / "git-project"
        repo.mkdir(parents=True, exist_ok=True)

        # Initialize a real git repository
        run_with_timeout(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)

        # Simulate running from a nested directory inside the repo
        nested = repo / "nested" / "dir"
        nested.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(nested)
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)

        root = resolve_project_root()
        assert root == repo

    def test_non_git_directory_raises_error_when_no_env_override(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When no git repo is present and no env override is set, resolution must fail."""
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("project_ROOT", raising=False)
        monkeypatch.delenv("project_PROJECT_ROOT", raising=False)

        workdir = tmp_path / "no-repo-here"
        workdir.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(workdir)

        with pytest.raises(EdisonPathError):
            resolve_project_root()


class TestMemoization:
    def test_memoization_prevents_repeated_git_calls(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        resolve_project_root should memoize the detected root so that repeated
        calls in a single process do not re-run filesystem/git operations.

        We verify this by checking the _PROJECT_ROOT_CACHE is populated after
        the first call and reused on subsequent calls.
        """
        repo = tmp_path / "memoized-repo"
        repo.mkdir(parents=True, exist_ok=True)
        run_with_timeout(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)

        monkeypatch.chdir(repo)
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)

        # Import the module and ensure cache starts empty
        import edison.core.utils.paths.resolver as resolver_module

        resolver_module._PROJECT_ROOT_CACHE = None

        # First call should populate the cache
        first_root = resolver_module.resolve_project_root()
        assert first_root == repo
        assert resolver_module._PROJECT_ROOT_CACHE == repo, "Cache should be populated after first call"

        # Second call should reuse the cached value
        second_root = resolver_module.resolve_project_root()
        assert second_root == repo
        assert resolver_module._PROJECT_ROOT_CACHE == repo, "Cache should still be the same value"

        # Verify both calls returned the same exact Path object (not just equal paths)
        assert first_root is not None and second_root is not None
