"""Tests for vendor CLI commands.

RED Phase: These tests define expected behavior for vendor CLI.
"""
from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from io import StringIO
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from helpers.env import TestGitRepo


def write_yaml(path: Path, content: str) -> None:
    """Helper to write YAML content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


class TestVendorListCommand:
    """Test 'edison vendor list' command."""

    def test_list_shows_configured_vendors(self, tmp_path: Path) -> None:
        """List command should show all configured vendors."""
        from edison.cli.vendor.list import main, register_args

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/anthropics/opencode.git
                  ref: main
                  path: vendors/opencode
                - name: speckit
                  url: https://github.com/example/speckit.git
                  ref: v1.0.0
                  path: vendors/speckit
            """,
        )

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--repo-root", str(tmp_path)])

        exit_code = main(args)

        assert exit_code == 0

    def test_list_tolerates_null_lock_commit(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """List command should not crash if lock file contains a null commit."""
        from edison.cli.vendor.list import main, register_args

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/anthropics/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )
        write_yaml(
            config_dir / "vendors.lock.yaml",
            """
            vendors:
              - name: opencode
                url: https://github.com/anthropics/opencode.git
                ref: main
                commit:
                path: vendors/opencode
            """,
        )

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--repo-root", str(tmp_path)])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "opencode" in captured.out

    def test_list_json_output(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """List command should support JSON output."""
        from edison.cli.vendor.list import main, register_args

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/anthropics/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--repo-root", str(tmp_path), "--json"])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        assert "vendors" in data
        assert len(data["vendors"]) == 1
        assert data["vendors"][0]["name"] == "opencode"

    def test_list_empty_when_no_vendors(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """List command should handle empty vendor config gracefully."""
        from edison.cli.vendor.list import main, register_args

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        # No vendors.yaml file

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--repo-root", str(tmp_path), "--json"])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        assert data["vendors"] == []


class TestVendorShowCommand:
    """Test 'edison vendor show' command."""

    def test_show_displays_vendor_details(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Show command should display details for a specific vendor."""
        from edison.cli.vendor.show import main, register_args

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/anthropics/opencode.git
                  ref: main
                  path: vendors/opencode
                  sparse:
                    - src/
            """,
        )

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["opencode", "--repo-root", str(tmp_path), "--json"])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        assert data["name"] == "opencode"
        assert data["url"] == "https://github.com/anthropics/opencode.git"
        assert data["sparse"] == ["src/"]

    def test_show_includes_lock_info(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Show command should include lock file info when available."""
        from edison.cli.vendor.show import main, register_args

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/anthropics/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )
        write_yaml(
            config_dir / "vendors.lock.yaml",
            """
            vendors:
              - name: opencode
                url: https://github.com/anthropics/opencode.git
                ref: main
                commit: abc123def456789
                path: vendors/opencode
            """,
        )

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["opencode", "--repo-root", str(tmp_path), "--json"])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        assert data["locked_commit"] == "abc123def456789"

    def test_show_error_for_unknown_vendor(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Show command should error for unknown vendor name."""
        from edison.cli.vendor.show import main, register_args

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources: []
            """,
        )

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["nonexistent", "--repo-root", str(tmp_path)])

        exit_code = main(args)

        assert exit_code != 0


class TestVendorSyncCommand:
    """Test 'edison vendor sync' command."""

    def test_sync_all_vendors(
        self, tmp_path: Path, git_repo: "TestGitRepo", capsys: pytest.CaptureFixture
    ) -> None:
        """Sync command should sync all configured vendors."""
        from edison.cli.vendor.sync import main, register_args

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

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--repo-root", str(tmp_path)])

        exit_code = main(args)

        assert exit_code == 0
        assert (tmp_path / "vendors" / "vendor1").exists()

    def test_sync_specific_vendor(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Sync command should support syncing a specific vendor."""
        from edison.cli.vendor.sync import main, register_args

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

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["vendor1", "--repo-root", str(tmp_path)])

        exit_code = main(args)

        assert exit_code == 0
        assert (tmp_path / "vendors" / "vendor1").exists()
        assert not (tmp_path / "vendors" / "vendor2").exists()

    def test_sync_json_output(
        self, tmp_path: Path, git_repo: "TestGitRepo", capsys: pytest.CaptureFixture
    ) -> None:
        """Sync command should support JSON output."""
        from edison.cli.vendor.sync import main, register_args

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

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--repo-root", str(tmp_path), "--json"])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["success"] is True


class TestVendorUpdateCommand:
    """Test 'edison vendor update' command."""

    def test_update_fetches_latest(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Update command should fetch latest and update checkout."""
        from edison.cli.vendor.sync import main as sync_main, register_args as sync_register
        from edison.cli.vendor.update import main, register_args

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

        # Initial sync
        sync_parser = argparse.ArgumentParser()
        sync_register(sync_parser)
        sync_args = sync_parser.parse_args(["--repo-root", str(tmp_path)])
        sync_main(sync_args)

        # Add new commit to "remote"
        (git_repo.repo_path / "new.txt").write_text("new", encoding="utf-8")
        git_repo.commit_all("Add new file")

        # Update
        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--repo-root", str(tmp_path)])

        exit_code = main(args)

        assert exit_code == 0

    def test_update_specific_vendor(
        self, tmp_path: Path, git_repo: "TestGitRepo"
    ) -> None:
        """Update command should support updating a specific vendor."""
        from edison.cli.vendor.update import main, register_args

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

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["vendor1", "--repo-root", str(tmp_path)])

        exit_code = main(args)

        assert exit_code == 0


class TestVendorGcCommand:
    """Test 'edison vendor gc' command."""

    def test_gc_removes_orphaned_caches(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """GC command should remove orphaned cache entries."""
        from edison.cli.vendor.gc import main, register_args

        cache_dir = tmp_path / ".cache" / "vendors"
        cache_dir.mkdir(parents=True)

        # Create orphaned cache
        orphaned = cache_dir / "orphaned.git"
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

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--repo-root", str(tmp_path)])

        exit_code = main(args)

        assert exit_code == 0
        assert not orphaned.exists()

    def test_gc_dry_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """GC command should support dry-run mode."""
        from edison.cli.vendor.gc import main, register_args

        cache_dir = tmp_path / ".cache" / "vendors"
        cache_dir.mkdir(parents=True)

        orphaned = cache_dir / "orphaned.git"
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

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--dry-run", "--repo-root", str(tmp_path)])

        exit_code = main(args)

        assert exit_code == 0
        assert orphaned.exists()  # Should not be deleted in dry-run

    def test_gc_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """GC command should support JSON output."""
        from edison.cli.vendor.gc import main, register_args

        cache_dir = tmp_path / ".cache" / "vendors"
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

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--json", "--repo-root", str(tmp_path)])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        assert "removed_mirrors" in data


class TestVendorCommandRegistration:
    """Test vendor command registration in CLI."""

    def test_vendor_subcommands_registered(self) -> None:
        """Vendor subcommands should be discoverable."""
        from edison.cli.vendor import SUBCOMMANDS

        expected_commands = {"list", "show", "sync", "update", "gc"}
        actual_commands = set(SUBCOMMANDS.keys())

        assert expected_commands <= actual_commands
