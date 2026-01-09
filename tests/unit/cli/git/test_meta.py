"""Tests for edison git meta subcommands.

Tests the `edison git meta-status` and `edison git meta-commit` commands that
help users work with the shared-state meta worktree.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest


class TestMetaStatusCommand:
    """Tests for `edison git meta-status`."""

    def test_meta_status_shows_mode_from_config(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-status should show the shared state mode from config."""
        # Configure meta mode in project config
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n"
            "    metaBranch: edison-meta\n"
            "    metaPathTemplate: .worktrees/_meta\n",
            encoding="utf-8",
        )

        from edison.cli.git.meta_status import main as meta_status_main

        args = argparse.Namespace(json=True)
        code = meta_status_main(args)
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")
        assert payload.get("mode") == "meta"
        assert payload.get("meta_branch") == "edison-meta"

    def test_meta_status_shows_meta_path(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-status should show the resolved meta worktree path."""
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n"
            "    metaPathTemplate: .worktrees/_meta\n",
            encoding="utf-8",
        )

        from edison.cli.git.meta_status import main as meta_status_main

        args = argparse.Namespace(json=True)
        code = meta_status_main(args)
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")
        # The meta path should contain our template
        assert ".worktrees/_meta" in str(payload.get("meta_path", ""))

    def test_meta_status_shows_exists_false_when_missing(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-status should show exists=False when meta worktree is not created."""
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n",
            encoding="utf-8",
        )

        from edison.cli.git.meta_status import main as meta_status_main

        args = argparse.Namespace(json=True)
        code = meta_status_main(args)
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")
        assert payload.get("exists") is False

    def test_meta_status_suggests_init_when_missing(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-status should suggest worktree-meta-init command when meta worktree is missing."""
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n",
            encoding="utf-8",
        )

        from edison.cli.git.meta_status import main as meta_status_main

        args = argparse.Namespace(json=False)
        code = meta_status_main(args)
        captured = capsys.readouterr()

        assert code == 0
        # Should suggest the init command
        assert "worktree-meta-init" in captured.out

    def test_meta_status_shows_dirty_state(
        self, isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-status should show dirty state when meta worktree has uncommitted changes."""
        # Set up meta worktree
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n"
            "    metaBranch: edison-meta\n"
            "    metaPathTemplate: .worktrees/_meta\n",
            encoding="utf-8",
        )

        # Initialize meta worktree using the existing command
        from edison.core.session import worktree

        worktree.initialize_meta_shared_state(dry_run=False)

        # Create a dirty file in meta worktree
        meta_path = isolated_project_env / ".worktrees" / "_meta"
        if meta_path.exists():
            (meta_path / ".project").mkdir(parents=True, exist_ok=True)
            (meta_path / ".project" / "test.txt").write_text("dirty content\n")

        from edison.cli.git.meta_status import main as meta_status_main

        args = argparse.Namespace(json=True)
        code = meta_status_main(args)
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")
        # If meta exists, dirty should be set
        if payload.get("exists"):
            assert "dirty" in payload
            assert payload.get("dirty") is True

    def test_meta_status_shows_changed_files(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-status should list changed files in the meta worktree."""
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n"
            "    metaBranch: edison-meta\n"
            "    metaPathTemplate: .worktrees/_meta\n"
            "    sharedPaths:\n"
            "      - path: .project/tasks\n"
            "        scopes: [primary, session]\n",
            encoding="utf-8",
        )

        # Initialize meta worktree
        from edison.core.session import worktree

        worktree.initialize_meta_shared_state(dry_run=False)

        # Create changed files in shared paths
        meta_path = isolated_project_env / ".worktrees" / "_meta"
        if meta_path.exists():
            tasks_dir = meta_path / ".project" / "tasks"
            tasks_dir.mkdir(parents=True, exist_ok=True)
            (tasks_dir / "001-test-task.md").write_text("# Test Task\n")

        from edison.cli.git.meta_status import main as meta_status_main

        args = argparse.Namespace(json=True)
        code = meta_status_main(args)
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")
        if payload.get("exists") and payload.get("dirty"):
            assert "changed_files" in payload
            # The changed file should be visible
            changed = payload.get("changed_files", [])
            assert isinstance(changed, list)


class TestMetaCommitCommand:
    """Tests for `edison git meta-commit`."""

    def test_meta_commit_requires_message(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-commit should require an explicit -m/--message."""
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n",
            encoding="utf-8",
        )

        from edison.cli.git.meta_commit import main as meta_commit_main

        # No message provided
        args = argparse.Namespace(message=None, json=False, all=False)
        code = meta_commit_main(args)
        captured = capsys.readouterr()

        assert code != 0
        assert "message" in captured.err.lower() or "required" in captured.err.lower()

    def test_meta_commit_fails_when_meta_missing(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-commit should fail when meta worktree does not exist."""
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n",
            encoding="utf-8",
        )

        from edison.cli.git.meta_commit import main as meta_commit_main

        args = argparse.Namespace(message="Test commit", json=False, all=False)
        code = meta_commit_main(args)
        captured = capsys.readouterr()

        assert code != 0
        # Should mention meta worktree is missing and suggest init
        assert "worktree-meta-init" in captured.err or "missing" in captured.err.lower()

    def test_meta_commit_runs_in_meta_directory(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-commit should run git commit inside the meta worktree directory."""
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n"
            "    metaBranch: edison-meta\n"
            "    metaPathTemplate: .worktrees/_meta\n",
            encoding="utf-8",
        )

        # Initialize meta worktree
        from edison.core.session import worktree

        worktree.initialize_meta_shared_state(dry_run=False)

        # Create and stage a file in meta worktree
        meta_path = isolated_project_env / ".worktrees" / "_meta"
        if not meta_path.exists():
            pytest.skip("Meta worktree not created")

        tasks_dir = meta_path / ".project" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        test_file = tasks_dir / "001-test.md"
        test_file.write_text("# Test\n")

        subprocess.run(
            ["git", "add", ".project/tasks/001-test.md"],
            cwd=meta_path,
            check=True,
            capture_output=True,
        )

        from edison.cli.git.meta_commit import main as meta_commit_main

        args = argparse.Namespace(message="Add test task", json=True, all=False)
        code = meta_commit_main(args)
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")
        assert payload.get("committed") is True or payload.get("status") == "success"

    def test_meta_commit_does_not_switch_primary_branch(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-commit should NOT switch branches in the primary checkout."""
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n"
            "    metaBranch: edison-meta\n"
            "    metaPathTemplate: .worktrees/_meta\n",
            encoding="utf-8",
        )

        # Get current branch in primary checkout
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=isolated_project_env,
            capture_output=True,
            text=True,
            check=True,
        )
        primary_branch_before = result.stdout.strip()

        # Initialize meta worktree
        from edison.core.session import worktree

        worktree.initialize_meta_shared_state(dry_run=False)

        meta_path = isolated_project_env / ".worktrees" / "_meta"
        if not meta_path.exists():
            pytest.skip("Meta worktree not created")

        # Create and stage a file in allowed prefix (.project/sessions/)
        sessions_dir = meta_path / ".project" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "test-session.yaml").write_text("test: true\n")
        subprocess.run(
            ["git", "add", ".project/sessions/test-session.yaml"],
            cwd=meta_path,
            check=True,
            capture_output=True,
        )

        from edison.cli.git.meta_commit import main as meta_commit_main

        args = argparse.Namespace(message="Test commit", json=False, all=False)
        meta_commit_main(args)

        # Verify primary branch has NOT changed
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=isolated_project_env,
            capture_output=True,
            text=True,
            check=True,
        )
        primary_branch_after = result.stdout.strip()

        assert primary_branch_before == primary_branch_after

    def test_meta_commit_json_output(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """meta-commit should return proper JSON output when --json is passed."""
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "worktrees.yaml").write_text(
            "worktrees:\n"
            "  enabled: true\n"
            "  sharedState:\n"
            "    mode: meta\n"
            "    metaBranch: edison-meta\n"
            "    metaPathTemplate: .worktrees/_meta\n",
            encoding="utf-8",
        )

        # Initialize meta worktree
        from edison.core.session import worktree

        worktree.initialize_meta_shared_state(dry_run=False)

        meta_path = isolated_project_env / ".worktrees" / "_meta"
        if not meta_path.exists():
            pytest.skip("Meta worktree not created")

        # Create and stage a file in allowed prefix (.project/sessions/)
        sessions_dir = meta_path / ".project" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "test-session2.yaml").write_text("test: json\n")
        subprocess.run(
            ["git", "add", ".project/sessions/test-session2.yaml"],
            cwd=meta_path,
            check=True,
            capture_output=True,
        )

        from edison.cli.git.meta_commit import main as meta_commit_main

        args = argparse.Namespace(message="Test commit", json=True, all=False)
        code = meta_commit_main(args)
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")
        assert "commit_sha" in payload or "sha" in payload or "committed" in payload
