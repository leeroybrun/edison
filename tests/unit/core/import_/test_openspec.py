"""Tests for OpenSpec import module.

Following STRICT TDD - tests written FIRST, implementation second.

Tests cover:
1. Parser: parse_openspec_source, list_open_spec_changes
2. Generator: generate_edison_task_from_openspec_change
3. Sync: sync_openspec_changes
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestParseOpenSpecSource:
    def test_parse_from_repo_root(self, tmp_path: Path) -> None:
        from edison.core.import_.openspec import parse_openspec_source

        repo = tmp_path / "repo"
        (repo / "openspec" / "changes" / "add-foo").mkdir(parents=True)
        (repo / "openspec" / "changes" / "add-foo" / "proposal.md").write_text(
            "# Add foo\n\n## Why\nBecause.\n\n## What Changes\n- ...\n",
            encoding="utf-8",
        )

        parsed = parse_openspec_source(repo)
        assert parsed.repo_root == repo
        assert parsed.openspec_dir == repo / "openspec"
        assert parsed.changes_dir == repo / "openspec" / "changes"

    def test_parse_from_openspec_dir(self, tmp_path: Path) -> None:
        from edison.core.import_.openspec import parse_openspec_source

        repo = tmp_path / "repo"
        openspec = repo / "openspec"
        (openspec / "changes").mkdir(parents=True)

        parsed = parse_openspec_source(openspec)
        assert parsed.repo_root == repo
        assert parsed.openspec_dir == openspec

    def test_parse_from_changes_dir(self, tmp_path: Path) -> None:
        from edison.core.import_.openspec import parse_openspec_source

        repo = tmp_path / "repo"
        changes = repo / "openspec" / "changes"
        changes.mkdir(parents=True)

        parsed = parse_openspec_source(changes)
        assert parsed.repo_root == repo
        assert parsed.changes_dir == changes

    def test_parse_rejects_missing_structure(self, tmp_path: Path) -> None:
        from edison.core.import_.openspec import parse_openspec_source, OpenSpecImportError

        repo = tmp_path / "repo"
        repo.mkdir()

        with pytest.raises(OpenSpecImportError, match="openspec directory not found"):
            parse_openspec_source(repo)


class TestListOpenSpecChanges:
    def test_lists_active_changes_excludes_archive(self, tmp_path: Path) -> None:
        from edison.core.import_.openspec import parse_openspec_source, list_openspec_changes

        repo = tmp_path / "repo"
        active = repo / "openspec" / "changes" / "add-foo"
        archived = repo / "openspec" / "changes" / "archive" / "2025-01-01-add-bar"
        active.mkdir(parents=True)
        archived.mkdir(parents=True)

        (active / "proposal.md").write_text("# Add foo\n\n## Why\nx\n\n## What Changes\n- x\n", encoding="utf-8")
        (archived / "proposal.md").write_text("# Add bar\n\n## Why\nx\n\n## What Changes\n- x\n", encoding="utf-8")

        src = parse_openspec_source(repo)
        changes = list_openspec_changes(src, include_archived=False)
        assert [c.change_id for c in changes] == ["add-foo"]


class TestSyncOpenSpecChanges:
    @pytest.fixture
    def repo_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Setup repository environment (same as SpecKit tests)."""
        from tests.helpers.fixtures import create_repo_with_git
        from tests.helpers.io_utils import write_yaml

        repo = create_repo_with_git(tmp_path)
        config_dir = repo / ".edison" / "config"

        # Minimal config for tasks + qa
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

    def test_sync_creates_one_task_per_change(self, repo_env: Path) -> None:
        from edison.core.import_.openspec import parse_openspec_source, sync_openspec_changes

        repo = repo_env
        change_dir = repo / "openspec" / "changes" / "add-foo"
        (change_dir / "specs" / "foo").mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# Add foo\n\n## Why\nx\n\n## What Changes\n- x\n", encoding="utf-8")
        (change_dir / "tasks.md").write_text("## Tasks\n- [ ] Do thing\n", encoding="utf-8")
        (change_dir / "specs" / "foo" / "spec.md").write_text(
            "## ADDED Requirements\n\n### Requirement: Foo\nThe system SHALL foo.\n\n#### Scenario: ok\n- **WHEN** x\n- **THEN** y\n",
            encoding="utf-8",
        )

        src = parse_openspec_source(repo)
        result = sync_openspec_changes(src, prefix="openspec", create_qa=False, dry_run=False, project_root=repo)

        assert "openspec-add-foo" in result.created
        assert (repo / ".project" / "tasks" / "todo" / "openspec-add-foo.md").exists()

    def test_sync_flags_removed_changes(self, repo_env: Path) -> None:
        from edison.core.import_.openspec import parse_openspec_source, sync_openspec_changes
        from edison.core.task.repository import TaskRepository
        from edison.core.task.models import Task

        repo = repo_env
        # Existing task with prefix but no matching change
        task_repo = TaskRepository(repo)
        task_repo.save(Task.create("openspec-add-removed", "Removed change", state="todo"))

        # Create a different change
        change_dir = repo / "openspec" / "changes" / "add-foo"
        change_dir.mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# Add foo\n\n## Why\nx\n\n## What Changes\n- x\n", encoding="utf-8")
        (change_dir / "specs" / "foo").mkdir(parents=True)
        (change_dir / "specs" / "foo" / "spec.md").write_text(
            "## ADDED Requirements\n\n### Requirement: Foo\nThe system SHALL foo.\n\n#### Scenario: ok\n- **WHEN** x\n- **THEN** y\n",
            encoding="utf-8",
        )

        src = parse_openspec_source(repo)
        result = sync_openspec_changes(src, prefix="openspec", create_qa=False, dry_run=False, project_root=repo)

        assert "openspec-add-removed" in result.flagged

