"""Tests for Edison CLI import speckit command.

Following STRICT TDD - tests written FIRST, implementation second.
"""

from __future__ import annotations

import argparse
import pytest
from pathlib import Path

from tests.helpers.fixtures import create_repo_with_git
from tests.helpers.io_utils import write_yaml


class TestImportSpeckitArgs:
    """Tests for argument registration."""

    def test_register_args_source_required(self):
        """Source argument is required."""
        from edison.cli.import_.speckit import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        # Verify source is a positional argument
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_register_args_accepts_source(self):
        """Source argument is accepted."""
        from edison.cli.import_.speckit import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        args = parser.parse_args(["specs/auth/"])
        assert args.source == "specs/auth/"

    def test_register_args_optional_flags(self):
        """Optional flags are registered."""
        from edison.cli.import_.speckit import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        args = parser.parse_args([
            "specs/auth/",
            "--prefix", "auth",
            "--dry-run",
            "--no-qa",
            "--json",
        ])

        assert args.source == "specs/auth/"
        assert args.prefix == "auth"
        assert args.dry_run is True
        assert args.no_qa is True
        assert args.json is True


class TestImportSpeckitCommand:
    """Tests for import speckit command execution."""

    @pytest.fixture
    def repo_env(self, tmp_path: Path, monkeypatch):
        """Setup repository environment."""
        repo = create_repo_with_git(tmp_path)
        config_dir = repo / ".edison" / "config"

        # Minimal config for tasks
        write_yaml(
            config_dir / "defaults.yaml",
            {
                "statemachine": {
                    "task": {
                        "states": {
                            "todo": {"allowed_transitions": [{"to": "wip"}]},
                            "wip": {"allowed_transitions": [{"to": "done"}]},
                            "done": {"allowed_transitions": []},
                        },
                    },
                    "qa": {
                        "states": {
                            "waiting": {"allowed_transitions": [{"to": "todo"}]},
                            "todo": {"allowed_transitions": [{"to": "wip"}]},
                            "wip": {"allowed_transitions": [{"to": "done"}]},
                            "done": {"allowed_transitions": []},
                        }
                    },
                },
                "semantics": {
                    "task": {"todo": "todo", "wip": "wip", "done": "done"},
                    "qa": {"waiting": "waiting", "todo": "todo", "wip": "wip", "done": "done"},
                },
            },
        )

        write_yaml(
            config_dir / "tasks.yaml",
            {
                "tasks": {
                    "paths": {
                        "root": ".project/tasks",
                        "qaRoot": ".project/qa",
                        "metaRoot": ".project/tasks/meta",
                    }
                }
            },
        )

        # Create task directories
        (repo / ".project" / "tasks" / "todo").mkdir(parents=True)
        (repo / ".project" / "tasks" / "wip").mkdir(parents=True)
        (repo / ".project" / "tasks" / "done").mkdir(parents=True)
        (repo / ".project" / "qa" / "waiting").mkdir(parents=True)

        monkeypatch.chdir(repo)
        return repo

    def test_main_imports_tasks(self, repo_env: Path):
        """Command imports tasks from SpecKit feature."""
        from edison.cli.import_.speckit import main, register_args

        # Create SpecKit feature
        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text(
            """
## Phase 1: Setup

- [ ] T001 Create project structure
- [ ] T002 [P] Initialize dependencies
"""
        )

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([str(feature_dir), "--repo-root", str(repo_env)])

        result = main(args)
        assert result == 0

        # Verify tasks created
        task_dir = repo_env / ".project" / "tasks" / "todo"
        assert (task_dir / "auth-T001.md").exists()
        assert (task_dir / "auth-T002.md").exists()

    def test_main_dry_run_no_changes(self, repo_env: Path):
        """Dry run shows changes without writing."""
        from edison.cli.import_.speckit import main, register_args

        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create model")

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            str(feature_dir),
            "--repo-root", str(repo_env),
            "--dry-run",
        ])

        result = main(args)
        assert result == 0

        # Verify no files created
        task_dir = repo_env / ".project" / "tasks" / "todo"
        assert not (task_dir / "auth-T001.md").exists()

    def test_main_custom_prefix(self, repo_env: Path):
        """Command uses custom prefix."""
        from edison.cli.import_.speckit import main, register_args

        feature_dir = repo_env / "specs" / "authentication"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create model")

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            str(feature_dir),
            "--repo-root", str(repo_env),
            "--prefix", "auth",
        ])

        result = main(args)
        assert result == 0

        # Verify task uses custom prefix
        task_dir = repo_env / ".project" / "tasks" / "todo"
        assert (task_dir / "auth-T001.md").exists()

    def test_main_no_qa_flag(self, repo_env: Path):
        """Command skips QA records with --no-qa."""
        from edison.cli.import_.speckit import main, register_args

        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create model")

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            str(feature_dir),
            "--repo-root", str(repo_env),
            "--no-qa",
        ])

        result = main(args)
        assert result == 0

        # Verify no QA record
        qa_dir = repo_env / ".project" / "qa" / "waiting"
        assert not (qa_dir / "auth-T001-qa.md").exists()

    def test_main_json_output(self, repo_env: Path, capsys):
        """Command outputs JSON when --json flag is set."""
        from edison.cli.import_.speckit import main, register_args
        import json

        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create model")

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            str(feature_dir),
            "--repo-root", str(repo_env),
            "--json",
        ])

        result = main(args)
        assert result == 0

        # Verify JSON output
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "created" in output
        assert "auth-T001" in output["created"]

    def test_main_missing_tasks_md(self, repo_env: Path):
        """Command fails when tasks.md is missing."""
        from edison.cli.import_.speckit import main, register_args

        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        # No tasks.md

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([str(feature_dir), "--repo-root", str(repo_env)])

        result = main(args)
        assert result == 1

    def test_main_missing_directory(self, repo_env: Path):
        """Command fails when directory doesn't exist."""
        from edison.cli.import_.speckit import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            str(repo_env / "nonexistent"),
            "--repo-root", str(repo_env),
        ])

        result = main(args)
        assert result == 1


class TestSummaryConstant:
    """Test the SUMMARY constant."""

    def test_summary_exists(self):
        """SUMMARY constant exists for CLI dispatcher."""
        from edison.cli.import_.speckit import SUMMARY

        assert isinstance(SUMMARY, str)
        assert len(SUMMARY) > 0
        assert "speckit" in SUMMARY.lower() or "import" in SUMMARY.lower()
