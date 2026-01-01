"""Tests for qa validate output format.

These tests verify that:
1. `qa validate --execute` always prints Worktree, Round, and Evidence path
2. `--worktree-path` override is respected
3. JSON mode includes worktree path info
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from io import StringIO
import sys

import pytest
import yaml


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _setup_minimal_validator_config(repo: Path) -> None:
    """Setup minimal validator config for testing."""
    cfg_dir = repo / ".edison" / "config"
    _write_yaml(
        cfg_dir / "validators.yaml",
        {
            "validation": {
                "validators": {
                    "test-validator": {
                        "name": "TestValidator",
                        "engine": "pal-mcp",
                        "fallback_engine": "pal-mcp",
                        "wave": "critical",
                        "always_run": True,
                        "blocking": True,
                        "triggers": ["*"],
                    },
                },
                "waves": [{"name": "critical"}],
            }
        },
    )


def _setup_task(repo: Path, task_id: str = "T001") -> None:
    """Create a minimal task file."""
    task_dir = repo / ".project" / "tasks" / "done"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / f"{task_id}.md").write_text(
        f"---\n"
        f"id: {task_id}\n"
        f"title: {task_id}\n"
        f"owner: test\n"
        f"created_at: '2025-12-15T00:00:00Z'\n"
        f"updated_at: '2025-12-15T00:00:00Z'\n"
        "---\n\n"
        f"# {task_id}\n",
        encoding="utf-8",
    )


class TestQaValidateOutputFormat:
    """Tests for qa validate output formatting."""

    def test_execute_prints_worktree_path(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """qa validate --execute should always print the Worktree path."""
        repo = isolated_project_env
        _setup_minimal_validator_config(repo)
        _setup_task(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        from edison.cli._dispatcher import main as cli_main

        # Execute validation (dry-run to avoid actual validator execution)
        code = cli_main(["qa", "validate", "T001", "--execute"])

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Should print Worktree path
        assert "Worktree:" in output, f"Expected 'Worktree:' in output: {output}"

    def test_execute_prints_round_number(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """qa validate --execute should always print the Round number."""
        repo = isolated_project_env
        _setup_minimal_validator_config(repo)
        _setup_task(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(["qa", "validate", "T001", "--execute"])

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Should print Round number
        assert "Round:" in output, f"Expected 'Round:' in output: {output}"

    def test_execute_prints_evidence_path(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """qa validate --execute should always print the Evidence directory path."""
        repo = isolated_project_env
        _setup_minimal_validator_config(repo)
        _setup_task(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(["qa", "validate", "T001", "--execute"])

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Should print Evidence path
        assert "Evidence:" in output, f"Expected 'Evidence:' in output: {output}"

    def test_json_mode_includes_worktree_in_output(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """qa validate --execute --json should include worktree_path in JSON output."""
        repo = isolated_project_env
        _setup_minimal_validator_config(repo)
        _setup_task(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(["qa", "validate", "T001", "--execute", "--json"])

        captured = capsys.readouterr()
        output = captured.out.strip()

        # Should be valid JSON with worktree_path
        payload = json.loads(output)
        assert "worktree_path" in payload, f"Expected 'worktree_path' in JSON: {payload}"


class TestQaValidateWorktreeOverride:
    """Tests for --worktree-path override."""

    def test_worktree_path_override_accepted(
        self, isolated_project_env: Path, tmp_path: Path
    ) -> None:
        """--worktree-path should be an accepted argument."""
        from edison.cli.qa import validate as validate_module

        parser = argparse.ArgumentParser()
        validate_module.register_args(parser)

        # Should not raise an error
        args = parser.parse_args(["T001", "--worktree-path", "/some/path"])

        assert hasattr(args, "worktree_path")
        assert args.worktree_path == "/some/path"

    def test_worktree_path_override_in_output(
        self, isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--worktree-path override should be reflected in output."""
        repo = isolated_project_env
        _setup_minimal_validator_config(repo)
        _setup_task(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        # Create an alternative worktree directory
        alt_worktree = tmp_path / "alt-worktree"
        alt_worktree.mkdir(parents=True, exist_ok=True)

        from edison.cli._dispatcher import main as cli_main

        code = cli_main([
            "qa", "validate", "T001", "--execute",
            "--worktree-path", str(alt_worktree),
        ])

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Should print the overridden worktree path
        assert str(alt_worktree) in output or "alt-worktree" in output, \
            f"Expected worktree path override in output: {output}"


class TestQaValidateHelpText:
    """Tests for updated help text."""

    def test_help_text_documents_worktree_path(self) -> None:
        """Help text should document --worktree-path option."""
        from edison.cli.qa import validate as validate_module

        parser = argparse.ArgumentParser()
        validate_module.register_args(parser)

        help_text = parser.format_help()

        assert "--worktree-path" in help_text, \
            f"Expected '--worktree-path' in help: {help_text}"

    def test_help_text_explains_worktree_path(self) -> None:
        """Help text should explain what --worktree-path does."""
        from edison.cli.qa import validate as validate_module

        parser = argparse.ArgumentParser()
        validate_module.register_args(parser)

        help_text = parser.format_help()

        # Should mention override or path for validation
        assert "worktree" in help_text.lower() or "path" in help_text.lower(), \
            f"Expected worktree path explanation in help: {help_text}"
