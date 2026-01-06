"""Tests for vendor sync operations (clone, update, checkout).

RED Phase: These tests define expected behavior for vendor sync.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from helpers.env import TestGitRepo


def write_yaml(path: Path, content: str) -> None:
    """Helper to write YAML content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


class TestVendorMirrorCache:
    """Test shared bare mirror cache management."""

    def test_mirror_cache_creates_bare_repo(self, tmp_path: Path) -> None:
        """Mirror cache should create a bare git repository."""
        from edison.core.vendors.cache import VendorMirrorCache

        cache = VendorMirrorCache(cache_dir=tmp_path / "cache")

        # Create a mock URL that would be hashed
        mirror_path = cache.get_mirror_path("https://github.com/example/repo.git")

        # Should return a path in the cache directory
        assert mirror_path.parent == tmp_path / "cache"
        # Path should be deterministic based on URL
        assert mirror_path.suffix == ".git"

    def test_mirror_path_is_deterministic(self, tmp_path: Path) -> None:
        """Same URL should always produce same mirror path."""
        from edison.core.vendors.cache import VendorMirrorCache

        cache = VendorMirrorCache(cache_dir=tmp_path / "cache")
        url = "https://github.com/example/repo.git"

        path1 = cache.get_mirror_path(url)
        path2 = cache.get_mirror_path(url)

        assert path1 == path2

    def test_different_urls_produce_different_paths(self, tmp_path: Path) -> None:
        """Different URLs should produce different mirror paths."""
        from edison.core.vendors.cache import VendorMirrorCache

        cache = VendorMirrorCache(cache_dir=tmp_path / "cache")

        path1 = cache.get_mirror_path("https://github.com/example/repo1.git")
        path2 = cache.get_mirror_path("https://github.com/example/repo2.git")

        assert path1 != path2

    def test_mirror_path_sanitizes_ssh_style_urls(self, tmp_path: Path) -> None:
        """Mirror path should handle SSH-style URLs without creating nested paths."""
        from edison.core.vendors.cache import VendorMirrorCache

        cache = VendorMirrorCache(cache_dir=tmp_path / "cache")
        url = "git@github.com:example/repo.git"
        mirror_path = cache.get_mirror_path(url)

        assert mirror_path.parent == tmp_path / "cache"
        assert mirror_path.suffix == ".git"
        assert "/" not in mirror_path.name

    def test_mirror_path_uses_fallback_name_when_extraction_empty(self, tmp_path: Path) -> None:
        """Mirror path should still be readable when URL parsing yields no name."""
        from edison.core.vendors.cache import VendorMirrorCache

        cache = VendorMirrorCache(cache_dir=tmp_path / "cache")
        url = "git@github.com:"
        mirror_path = cache.get_mirror_path(url)

        assert mirror_path.name.startswith("mirror-")


class TestVendorCheckout:
    """Test project-scoped worktree checkout."""

    def test_checkout_creates_worktree_from_mirror(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Checkout should create a worktree from the cached mirror."""
        from edison.core.vendors.checkout import VendorCheckout
        from edison.core.vendors.models import VendorSource

        source = VendorSource(
            name="opencode",
            url=str(git_repo.repo_path),  # Use local test repo as "remote"
            ref="main",
            path="vendors/opencode",
        )

        checkout = VendorCheckout(
            repo_root=tmp_path,
            cache_dir=tmp_path / ".cache" / "vendors",
        )

        # Sync should create the vendor directory
        result = checkout.sync(source)

        assert result.success
        assert (tmp_path / "vendors" / "opencode").exists()

    def test_checkout_resolves_ref_to_commit(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Checkout should resolve ref (branch/tag) to concrete commit SHA."""
        from edison.core.vendors.checkout import VendorCheckout
        from edison.core.vendors.models import VendorSource

        source = VendorSource(
            name="opencode",
            url=str(git_repo.repo_path),
            ref="main",
            path="vendors/opencode",
        )

        checkout = VendorCheckout(
            repo_root=tmp_path,
            cache_dir=tmp_path / ".cache" / "vendors",
        )

        result = checkout.sync(source)

        # Should have resolved commit SHA (40 hex chars)
        assert result.commit is not None
        assert len(result.commit) == 40
        assert all(c in "0123456789abcdef" for c in result.commit)

    def test_checkout_refuses_paths_outside_repo_root(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Checkout should refuse creating paths outside repo root."""
        from edison.core.vendors.checkout import VendorCheckout
        from edison.core.vendors.models import VendorSource

        repo_root = tmp_path / "repo"
        repo_root.mkdir(parents=True, exist_ok=True)

        source = VendorSource(
            name="opencode",
            url=str(git_repo.repo_path),
            ref="HEAD",
            path="../escape/opencode",
        )

        checkout = VendorCheckout(
            repo_root=repo_root,
            cache_dir=tmp_path / ".cache" / "vendors",
        )

        result = checkout.sync(source)
        assert result.success is False
        assert "outside repo root" in (result.error or "").lower()
        assert not (tmp_path / "escape" / "opencode").exists()

    def test_checkout_supports_sparse_checkout(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Checkout should support sparse checkout paths."""
        from edison.core.vendors.checkout import VendorCheckout
        from edison.core.vendors.models import VendorSource

        # Create a file in the test repo to enable sparse checkout testing
        (git_repo.repo_path / "src" / "main.py").parent.mkdir(parents=True)
        (git_repo.repo_path / "src" / "main.py").write_text("# main", encoding="utf-8")
        (git_repo.repo_path / "docs" / "README.md").parent.mkdir(parents=True)
        (git_repo.repo_path / "docs" / "README.md").write_text("# docs", encoding="utf-8")
        git_repo.commit_all("Add src and docs")

        source = VendorSource(
            name="opencode",
            url=str(git_repo.repo_path),
            ref="main",
            path="vendors/opencode",
            sparse=["src/"],
        )

        checkout = VendorCheckout(
            repo_root=tmp_path,
            cache_dir=tmp_path / ".cache" / "vendors",
        )

        result = checkout.sync(source)

        assert result.success
        # src/ should exist, docs/ should not
        vendor_path = tmp_path / "vendors" / "opencode"
        assert (vendor_path / "src" / "main.py").exists()
        # docs/ should not be checked out due to sparse
        assert not (vendor_path / "docs").exists()

    def test_checkout_idempotent(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Multiple syncs should be idempotent."""
        from edison.core.vendors.checkout import VendorCheckout
        from edison.core.vendors.models import VendorSource

        source = VendorSource(
            name="opencode",
            url=str(git_repo.repo_path),
            ref="main",
            path="vendors/opencode",
        )

        checkout = VendorCheckout(
            repo_root=tmp_path,
            cache_dir=tmp_path / ".cache" / "vendors",
        )

        result1 = checkout.sync(source)
        result2 = checkout.sync(source)

        assert result1.commit == result2.commit
        assert (tmp_path / "vendors" / "opencode").exists()


class TestVendorSync:
    """Test full vendor sync workflow."""

    def test_sync_all_vendors(self, tmp_path: Path, git_repo: "TestGitRepo") -> None:
        """Sync should process all configured vendor sources."""
        from edison.core.vendors.sync import VendorSyncManager

        # Configure two vendors
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            f"""
            vendors:
              cacheDir: {tmp_path / ".cache" / "vendors"}
              sources:
                - name: vendor1
                  url: {git_repo.repo_path}
                  ref: main
                  path: vendors/vendor1
                - name: vendor2
                  url: {git_repo.repo_path}
                  ref: main
                  path: vendors/vendor2
            """,
        )

        manager = VendorSyncManager(repo_root=tmp_path)
        results = manager.sync_all()

        assert len(results) == 2
        assert all(r.success for r in results)
        assert (tmp_path / "vendors" / "vendor1").exists()
        assert (tmp_path / "vendors" / "vendor2").exists()

    def test_sync_updates_lock_file(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Sync should update the lock file with resolved commits."""
        from edison.core.vendors.sync import VendorSyncManager

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            f"""
            vendors:
              cacheDir: {tmp_path / ".cache" / "vendors"}
              sources:
                - name: vendor1
                  url: {git_repo.repo_path}
                  ref: main
                  path: vendors/vendor1
            """,
        )

        manager = VendorSyncManager(repo_root=tmp_path)
        manager.sync_all()

        lock_path = config_dir / "vendors.lock.yaml"
        assert lock_path.exists()

        import yaml
        content = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
        assert len(content["vendors"]) == 1
        assert content["vendors"][0]["name"] == "vendor1"
        assert len(content["vendors"][0]["commit"]) == 40

    def test_sync_single_vendor(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Sync should support syncing a single vendor by name."""
        from edison.core.vendors.sync import VendorSyncManager

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            f"""
            vendors:
              cacheDir: {tmp_path / ".cache" / "vendors"}
              sources:
                - name: vendor1
                  url: {git_repo.repo_path}
                  ref: main
                  path: vendors/vendor1
                - name: vendor2
                  url: {git_repo.repo_path}
                  ref: main
                  path: vendors/vendor2
            """,
        )

        manager = VendorSyncManager(repo_root=tmp_path)
        result = manager.sync_vendor("vendor1")

        assert result.success
        assert (tmp_path / "vendors" / "vendor1").exists()
        # vendor2 should NOT be synced
        assert not (tmp_path / "vendors" / "vendor2").exists()


class TestVendorUpdate:
    """Test vendor update (re-fetch and checkout new ref)."""

    def test_update_fetches_new_commits(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Update should fetch new commits from remote."""
        from edison.core.vendors.sync import VendorSyncManager

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            f"""
            vendors:
              cacheDir: {tmp_path / ".cache" / "vendors"}
              sources:
                - name: vendor1
                  url: {git_repo.repo_path}
                  ref: main
                  path: vendors/vendor1
            """,
        )

        manager = VendorSyncManager(repo_root=tmp_path)

        # Initial sync
        results1 = manager.sync_all()
        commit1 = results1[0].commit

        # Add a new commit to the "remote"
        (git_repo.repo_path / "new_file.txt").write_text("new content", encoding="utf-8")
        git_repo.commit_all("Add new file")

        # Update should fetch new commit
        results2 = manager.update_all()
        commit2 = results2[0].commit

        assert commit1 != commit2

    def test_update_single_vendor(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Update should support updating a single vendor by name."""
        from edison.core.vendors.sync import VendorSyncManager

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            f"""
            vendors:
              cacheDir: {tmp_path / ".cache" / "vendors"}
              sources:
                - name: vendor1
                  url: {git_repo.repo_path}
                  ref: main
                  path: vendors/vendor1
            """,
        )

        manager = VendorSyncManager(repo_root=tmp_path)
        manager.sync_all()

        # Add new commit
        (git_repo.repo_path / "new_file.txt").write_text("new content", encoding="utf-8")
        git_repo.commit_all("Add new file")

        result = manager.update_vendor("vendor1")
        assert result.success


class TestVendorGarbageCollection:
    """Test cleanup of unused vendor cache entries."""

    def test_gc_removes_orphaned_mirrors(self, tmp_path: Path) -> None:
        """GC should remove mirror caches not referenced in config."""
        from edison.core.vendors.gc import VendorGarbageCollector

        cache_dir = tmp_path / ".cache" / "vendors"
        cache_dir.mkdir(parents=True)

        # Create orphaned mirror directory
        orphaned = cache_dir / "orphaned-abc123.git"
        orphaned.mkdir()
        (orphaned / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")

        # Configure no vendors but specify cache dir
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            f"""
            vendors:
              cacheDir: {cache_dir}
              sources: []
            """,
        )

        gc = VendorGarbageCollector(repo_root=tmp_path)
        result = gc.collect()

        assert len(result.removed_mirrors) == 1
        assert not orphaned.exists()

    def test_gc_preserves_referenced_mirrors(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """GC should preserve mirrors that are still referenced."""
        from edison.core.vendors.sync import VendorSyncManager
        from edison.core.vendors.gc import VendorGarbageCollector

        cache_dir = tmp_path / ".cache" / "vendors"
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)

        write_yaml(
            config_dir / "vendors.yaml",
            f"""
            vendors:
              cacheDir: {cache_dir}
              sources:
                - name: vendor1
                  url: {git_repo.repo_path}
                  ref: main
                  path: vendors/vendor1
            """,
        )

        # Sync to create mirror
        manager = VendorSyncManager(repo_root=tmp_path)
        manager.sync_all()

        # GC should not remove the referenced mirror
        gc = VendorGarbageCollector(repo_root=tmp_path)
        result = gc.collect()

        assert len(result.removed_mirrors) == 0
        # Mirror should still exist
        assert any(cache_dir.iterdir())

    def test_gc_dry_run_mode(self, tmp_path: Path) -> None:
        """GC dry run should report but not delete."""
        from edison.core.vendors.gc import VendorGarbageCollector

        cache_dir = tmp_path / ".cache" / "vendors"
        cache_dir.mkdir(parents=True)

        orphaned = cache_dir / "orphaned-abc123.git"
        orphaned.mkdir()
        (orphaned / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            f"""
            vendors:
              cacheDir: {cache_dir}
              sources: []
            """,
        )

        gc = VendorGarbageCollector(repo_root=tmp_path)
        result = gc.collect(dry_run=True)

        assert len(result.removed_mirrors) == 1  # Would be removed
        assert orphaned.exists()  # Still exists after dry run
