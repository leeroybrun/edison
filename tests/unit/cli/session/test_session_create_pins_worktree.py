"""Test that session create outputs worktree pinning status and session-id file path.

Task: 047-session-create-auto-write-worktree-session-id

This test verifies:
1. `edison session create` JSON output includes `sessionIdFilePath` and `worktreePinned`
2. Human output explains worktree pinning status
3. `.session-id` file exists in the created worktree management dir
4. Session resolution works from within the worktree without AGENTS_SESSION env var
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml


def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def _enable_worktrees(isolated_project_env: Path, tmp_path: Path) -> None:
    """Configure worktrees to be enabled for the test."""
    cfg_dir = isolated_project_env / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "worktrees.yml").write_text(
        yaml.safe_dump(
            {
                "worktrees": {
                    "enabled": True,
                    "baseBranch": "main",
                    "baseDirectory": str(tmp_path / "worktrees"),
                    "archiveDirectory": str(tmp_path / "worktrees" / "_archived"),
                    "branchPrefix": "session/",
                }
            }
        ),
        encoding="utf-8",
    )


class TestSessionCreateWorktreePinningJsonOutput:
    """Test JSON output includes worktree pinning fields."""

    def test_json_output_includes_session_id_file_path_when_worktree_created(
        self, isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """JSON output should include sessionIdFilePath when worktree is created."""
        _enable_worktrees(isolated_project_env, tmp_path)

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(
            [
                "session",
                "create",
                "--session-id",
                "test-session-pin-json",
                "--owner",
                "tester",
                "--json",
            ]
        )
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")

        # Verify new fields exist
        assert "sessionIdFilePath" in payload, "sessionIdFilePath should be in JSON output"
        assert "worktreePinned" in payload, "worktreePinned should be in JSON output"

    def test_json_output_session_id_file_path_is_correct(
        self, isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """sessionIdFilePath should point to the .session-id file inside the worktree."""
        _enable_worktrees(isolated_project_env, tmp_path)

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(
            [
                "session",
                "create",
                "--session-id",
                "test-session-path-correct",
                "--owner",
                "tester",
                "--json",
            ]
        )
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")

        session_id_file_path = payload.get("sessionIdFilePath")
        assert session_id_file_path is not None, "sessionIdFilePath should be present"

        # The path should end with .project/.session-id (or equivalent management dir)
        assert ".session-id" in session_id_file_path, "sessionIdFilePath should reference .session-id file"

    def test_json_output_worktree_pinned_is_true_when_session_id_file_exists(
        self, isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """worktreePinned should be true when .session-id file was successfully created."""
        _enable_worktrees(isolated_project_env, tmp_path)

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(
            [
                "session",
                "create",
                "--session-id",
                "test-session-pinned-true",
                "--owner",
                "tester",
                "--json",
            ]
        )
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")

        assert payload.get("worktreePinned") is True, "worktreePinned should be True when worktree is created"

    def test_json_output_no_worktree_fields_when_no_worktree_flag(
        self, isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When --no-worktree is passed, worktreePinned should be False and no file path."""
        _enable_worktrees(isolated_project_env, tmp_path)

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(
            [
                "session",
                "create",
                "--session-id",
                "test-session-no-wt",
                "--owner",
                "tester",
                "--no-worktree",
                "--json",
            ]
        )
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")

        assert payload.get("worktreePinned") is False, "worktreePinned should be False when --no-worktree"
        assert payload.get("sessionIdFilePath") is None, "sessionIdFilePath should be None when --no-worktree"


class TestSessionCreateWorktreePinningHumanOutput:
    """Test human-readable output includes worktree pinning information."""

    def test_human_output_mentions_session_id_file_when_worktree_created(
        self, isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Human output should mention the .session-id file when worktree is created."""
        _enable_worktrees(isolated_project_env, tmp_path)

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(
            [
                "session",
                "create",
                "--session-id",
                "test-session-human-output",
                "--owner",
                "tester",
            ]
        )
        captured = capsys.readouterr()

        assert code == 0
        output = captured.out

        # Should mention pinned or session-id file
        assert "pinned" in output.lower() or ".session-id" in output, (
            "Human output should mention pinning or .session-id file"
        )


class TestSessionCreateSessionIdFileExists:
    """Test that .session-id file is actually created in the worktree."""

    def test_session_id_file_exists_in_worktree_management_dir(
        self, isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """After session create, .session-id file should exist in the worktree."""
        _enable_worktrees(isolated_project_env, tmp_path)

        from edison.cli._dispatcher import main as cli_main

        session_id = "test-session-file-exists"

        code = cli_main(
            [
                "session",
                "create",
                "--session-id",
                session_id,
                "--owner",
                "tester",
                "--json",
            ]
        )
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")

        worktree_path = payload.get("session", {}).get("git", {}).get("worktreePath")
        assert worktree_path is not None, "Session should have worktreePath"

        # Check the .session-id file exists
        session_id_file = Path(worktree_path) / ".project" / ".session-id"
        assert session_id_file.exists(), f".session-id file should exist at {session_id_file}"
        assert session_id_file.read_text(encoding="utf-8").strip() == session_id


class TestSessionResolutionFromWorktree:
    """Test that session resolution works from within the worktree without env vars."""

    def test_session_status_works_from_worktree_without_env_var(
        self, isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Running session status from within worktree should work without AGENTS_SESSION."""
        _enable_worktrees(isolated_project_env, tmp_path)

        from edison.cli._dispatcher import main as cli_main

        session_id = "test-session-resolve-from-wt"

        # Create session
        code = cli_main(
            [
                "session",
                "create",
                "--session-id",
                session_id,
                "--owner",
                "tester",
                "--json",
            ]
        )
        captured = capsys.readouterr()

        assert code == 0
        payload = json.loads(captured.out or "{}")

        worktree_path = payload.get("session", {}).get("git", {}).get("worktreePath")
        assert worktree_path is not None

        # Clear AGENTS_SESSION env var and change to worktree directory
        monkeypatch.delenv("AGENTS_SESSION", raising=False)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(worktree_path))
        monkeypatch.chdir(worktree_path)

        # Session status should still work via .session-id file
        code = cli_main(["session", "status", "--json"])
        captured = capsys.readouterr()

        assert code == 0
        status_payload = json.loads(captured.out or "{}")
        assert status_payload.get("id") == session_id, "Session should be resolved via .session-id file"
