from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Generator

import pytest

from edison.core.utils.paths import (
    EdisonPathError,
    PathResolver,
    resolve_project_root,
)
# We'll import the modules we're refactoring to ensure they still work/redirect
from edison.core.utils import git as git_utils
from edison.core.utils import subprocess as subprocess_utils
from edison.core.task import paths as task_paths
from edison.core.composition import includes as composition_includes
from edison.core.composition.registries import guidelines as composition_guidelines
# from edison.core.adapters.sync import zen as zen_adapter
from edison.core.adapters.sync import cursor as cursor_adapter


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Creates a temporary git repository and yields its path."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    
    # Create a commit so HEAD exists (sometimes needed)
    (repo_path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True, capture_output=True)
    
    yield repo_path


@pytest.fixture(autouse=True)
def _reset_path_caches() -> Generator[None, None, None]:
    """Reset internal caches before each test."""
    import edison.core.utils.paths.resolver.project as project_mod
    from edison.core.task import paths as task_paths_mod

    project_mod._PROJECT_ROOT_CACHE = None
    task_paths_mod._ROOT_CACHE = None

    yield

    project_mod._PROJECT_ROOT_CACHE = None
    task_paths_mod._ROOT_CACHE = None


class TestRepoRootConsolidation:
    
    def test_canonical_implementation_works(self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify the canonical PathResolver works as expected."""
        monkeypatch.chdir(temp_git_repo)
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        
        root = resolve_project_root()
        assert root == temp_git_repo
        assert root.samefile(temp_git_repo)

    def test_utils_git_get_repo_root_delegates(self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that utils.git.get_repo_root delegates to canonical implementation."""
        monkeypatch.chdir(temp_git_repo)
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        
        root = git_utils.get_repo_root()
        assert root == temp_git_repo
        
        # Test with explicit path
        subdir = temp_git_repo / "subdir"
        subdir.mkdir()
        root_from_subdir = git_utils.get_repo_root(start_path=subdir)
        assert root_from_subdir == temp_git_repo

    def test_env_var_override_consistency(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that AGENTS_PROJECT_ROOT override works consistently across accessors."""
        fake_root = tmp_path / "fake_root"
        fake_root.mkdir()
        
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(fake_root))
        
        # Canonical
        assert resolve_project_root() == fake_root
        
        # utils.git
        assert git_utils.get_repo_root() == fake_root
        
        # task.paths (ensure it picks up the override via canonical)
        assert task_paths._get_root() == fake_root

    def test_composition_wrappers_use_canonical(self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that composition modules' _repo_root wrappers work."""
        monkeypatch.chdir(temp_git_repo)
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        
        # reset overrides if any (though they are module level, so might persist)
        composition_includes._REPO_ROOT_OVERRIDE = None
        
        assert composition_includes._repo_root() == temp_git_repo
        assert composition_guidelines._repo_root() == temp_git_repo

    def test_utils_subprocess_timeout_context(self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that subprocess timeout configuration can resolve root."""
        monkeypatch.chdir(temp_git_repo)
        
        # This calls _resolve_repo_root internally
        # We just want to ensure it doesn't crash and finds the root to load config (even if config is empty)
        timeout = subprocess_utils.configured_timeout(["git", "status"])
        assert isinstance(timeout, float)
        assert timeout > 0

    def test_adapters_sync_wrappers(self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that adapter sync modules use canonical root resolution."""
        monkeypatch.chdir(temp_git_repo)
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        
        # Zen Sync
        # zen = zen_adapter.ZenSync()
        # assert zen.repo_root == temp_git_repo
        
        # Cursor Sync
        cursor = cursor_adapter.CursorSync()
        assert cursor.repo_root == temp_git_repo

    def test_from_subdirectory(self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test resolution from a subdirectory."""
        subdir = temp_git_repo / "deep" / "nested" / "dir"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        
        assert resolve_project_root() == temp_git_repo
        assert git_utils.get_repo_root() == temp_git_repo

    def test_caching_behavior(self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that caching is effective (and consistent)."""
        monkeypatch.chdir(temp_git_repo)
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)

        # Access module-level cache variable from the correct module
        import edison.core.utils.paths.resolver.project as project_mod

        # First call populates cache
        root1 = resolve_project_root()
        cache_val = project_mod._PROJECT_ROOT_CACHE
        assert cache_val == temp_git_repo

        # Second call uses cache
        root2 = resolve_project_root()
        assert root2 is root1 # Same object if cached

        # utils.git should also respect/use this cache via delegation
        root3 = git_utils.get_repo_root()
        assert root3 == temp_git_repo
