"""Tests for Edison CLI import openspec command.

Following STRICT TDD - tests written FIRST, implementation second.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from tests.helpers.fixtures import create_repo_with_git
from tests.helpers.io_utils import write_yaml


class TestImportOpenSpecArgs:
    def test_register_args_source_required(self) -> None:
        from edison.cli.import_.openspec import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_register_args_accepts_source(self) -> None:
        from edison.cli.import_.openspec import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        args = parser.parse_args(["."])
        assert args.source == "."

    def test_register_args_optional_flags(self) -> None:
        from edison.cli.import_.openspec import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        args = parser.parse_args([
            ".",
            "--prefix", "os",
            "--dry-run",
            "--no-qa",
            "--json",
            "--include-archived",
        ])

        assert args.prefix == "os"
        assert args.dry_run is True
        assert args.no_qa is True
        assert args.json is True
        assert args.include_archived is True


class TestImportOpenSpecCommand:
    @pytest.fixture
    def repo_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        repo = create_repo_with_git(tmp_path)
        config_dir = repo / ".edison" / "config"

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

        (repo / ".project" / "tasks" / "todo").mkdir(parents=True)
        (repo / ".project" / "tasks" / "wip").mkdir(parents=True)
        (repo / ".project" / "tasks" / "done").mkdir(parents=True)
        (repo / ".project" / "qa" / "waiting").mkdir(parents=True)

        monkeypatch.chdir(repo)
        return repo

    def test_main_imports_changes(self, repo_env: Path) -> None:
        from edison.cli.import_.openspec import main, register_args

        change_dir = repo_env / "openspec" / "changes" / "add-foo"
        (change_dir / "specs" / "foo").mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# Add foo\n\n## Why\nx\n\n## What Changes\n- x\n", encoding="utf-8")
        (change_dir / "specs" / "foo" / "spec.md").write_text(
            "## ADDED Requirements\n\n### Requirement: Foo\nThe system SHALL foo.\n\n#### Scenario: ok\n- **WHEN** x\n- **THEN** y\n",
            encoding="utf-8",
        )

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([".", "--repo-root", str(repo_env)])

        rc = main(args)
        assert rc == 0
        assert (repo_env / ".project" / "tasks" / "todo" / "openspec-add-foo.md").exists()

    def test_main_json_output(self, repo_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from edison.cli.import_.openspec import main, register_args

        change_dir = repo_env / "openspec" / "changes" / "add-foo"
        (change_dir / "specs" / "foo").mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# Add foo\n\n## Why\nx\n\n## What Changes\n- x\n", encoding="utf-8")
        (change_dir / "specs" / "foo" / "spec.md").write_text(
            "## ADDED Requirements\n\n### Requirement: Foo\nThe system SHALL foo.\n\n#### Scenario: ok\n- **WHEN** x\n- **THEN** y\n",
            encoding="utf-8",
        )

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([".", "--repo-root", str(repo_env), "--json"])

        rc = main(args)
        assert rc == 0

        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert "created" in payload
        assert "openspec-add-foo" in payload["created"]

