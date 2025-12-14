"""Tests for SpecKit import module.

Following STRICT TDD - tests written FIRST, implementation second.

Tests cover:
1. Parser: parse_tasks_md, parse_feature_folder
2. Generator: generate_edison_task, generate_task_description
3. Sync: sync_speckit_feature
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import List


# =============================================================================
# PARSER TESTS
# =============================================================================


class TestParseTasksMd:
    """Tests for parse_tasks_md function."""

    def test_parse_simple_task(self):
        """Parse a simple task with just ID and description."""
        from edison.core.import_.speckit import parse_tasks_md

        content = "- [ ] T001 Create project structure"
        tasks = parse_tasks_md(content)

        assert len(tasks) == 1
        assert tasks[0].id == "T001"
        assert tasks[0].description == "Create project structure"
        assert tasks[0].parallel is False
        assert tasks[0].user_story is None
        assert tasks[0].completed is False

    def test_parse_task_with_parallel_marker(self):
        """Parse task with [P] parallel marker."""
        from edison.core.import_.speckit import parse_tasks_md

        content = "- [ ] T005 [P] Configure linting tools"
        tasks = parse_tasks_md(content)

        assert len(tasks) == 1
        assert tasks[0].id == "T005"
        assert tasks[0].parallel is True
        assert tasks[0].description == "Configure linting tools"

    def test_parse_task_with_user_story(self):
        """Parse task with [US1] user story marker."""
        from edison.core.import_.speckit import parse_tasks_md

        content = "- [ ] T012 [US1] Create User model in src/models/user.py"
        tasks = parse_tasks_md(content)

        assert len(tasks) == 1
        assert tasks[0].id == "T012"
        assert tasks[0].user_story == "US1"
        assert tasks[0].description == "Create User model in src/models/user.py"
        assert tasks[0].target_file == "src/models/user.py"

    def test_parse_task_with_all_markers(self):
        """Parse task with both [P] and [US#] markers."""
        from edison.core.import_.speckit import parse_tasks_md

        content = "- [ ] T015 [P] [US2] Create OrderService in src/services/order.py"
        tasks = parse_tasks_md(content)

        assert len(tasks) == 1
        assert tasks[0].id == "T015"
        assert tasks[0].parallel is True
        assert tasks[0].user_story == "US2"
        assert tasks[0].target_file == "src/services/order.py"

    def test_parse_completed_task(self):
        """Parse a completed task [x]."""
        from edison.core.import_.speckit import parse_tasks_md

        content = "- [x] T001 Create project structure"
        tasks = parse_tasks_md(content)

        assert len(tasks) == 1
        assert tasks[0].completed is True

    def test_parse_completed_task_uppercase(self):
        """Parse a completed task [X] (uppercase)."""
        from edison.core.import_.speckit import parse_tasks_md

        content = "- [X] T001 Create project structure"
        tasks = parse_tasks_md(content)

        assert len(tasks) == 1
        assert tasks[0].completed is True

    def test_parse_multiple_tasks(self):
        """Parse multiple tasks from content."""
        from edison.core.import_.speckit import parse_tasks_md

        content = """
## Phase 1: Setup

- [ ] T001 Create project structure
- [ ] T002 [P] Initialize dependencies
- [x] T003 Configure linting

## Phase 2: User Story 1

- [ ] T010 [US1] Create User model
- [ ] T011 [P] [US1] Create UserService
"""
        tasks = parse_tasks_md(content)

        assert len(tasks) == 5
        assert tasks[0].id == "T001"
        assert tasks[1].id == "T002"
        assert tasks[1].parallel is True
        assert tasks[2].id == "T003"
        assert tasks[2].completed is True
        assert tasks[3].id == "T010"
        assert tasks[3].user_story == "US1"
        assert tasks[4].id == "T011"
        assert tasks[4].parallel is True
        assert tasks[4].user_story == "US1"

    def test_parse_extracts_file_path_from_description(self):
        """Extract file path from task description."""
        from edison.core.import_.speckit import parse_tasks_md

        content = "- [ ] T012 Create User model in src/models/user.py"
        tasks = parse_tasks_md(content)

        assert tasks[0].target_file == "src/models/user.py"

    def test_parse_extracts_file_path_various_formats(self):
        """Extract file path from various description formats."""
        from edison.core.import_.speckit import parse_tasks_md

        # Format: "in path/to/file.py"
        content1 = "- [ ] T001 Create model in src/models/user.py"
        tasks1 = parse_tasks_md(content1)
        assert tasks1[0].target_file == "src/models/user.py"

        # Format: "at path/to/file.ts"
        content2 = "- [ ] T002 Add component at src/components/Button.tsx"
        tasks2 = parse_tasks_md(content2)
        assert tasks2[0].target_file == "src/components/Button.tsx"

        # Format: no file path
        content3 = "- [ ] T003 Configure environment variables"
        tasks3 = parse_tasks_md(content3)
        assert tasks3[0].target_file is None

    def test_parse_detects_phase_from_context(self):
        """Detect phase from section headers."""
        from edison.core.import_.speckit import parse_tasks_md

        content = """
## Phase 1: Setup

- [ ] T001 Create project structure

## Phase 2: Foundational

- [ ] T004 Setup database

## Phase 3: User Story 1 - Authentication

- [ ] T010 [US1] Create User model

## Phase N: Polish

- [ ] T099 Documentation updates
"""
        tasks = parse_tasks_md(content)

        assert tasks[0].phase == "setup"
        assert tasks[1].phase == "foundational"
        assert tasks[2].phase == "user-story-1"
        assert tasks[3].phase == "polish"

    def test_parse_ignores_non_task_lines(self):
        """Ignore lines that are not tasks."""
        from edison.core.import_.speckit import parse_tasks_md

        content = """
# Tasks: Auth Feature

Some description text.

**Prerequisites**: plan.md

## Phase 1: Setup

- [ ] T001 Create project structure
- This is not a task
- [ ] T002 Initialize dependencies

**Checkpoint**: Setup complete
"""
        tasks = parse_tasks_md(content)

        assert len(tasks) == 2
        assert tasks[0].id == "T001"
        assert tasks[1].id == "T002"

    def test_parse_handles_empty_content(self):
        """Handle empty content gracefully."""
        from edison.core.import_.speckit import parse_tasks_md

        tasks = parse_tasks_md("")
        assert tasks == []

    def test_parse_handles_no_tasks(self):
        """Handle content with no tasks."""
        from edison.core.import_.speckit import parse_tasks_md

        content = """
# Tasks

No tasks here yet.
"""
        tasks = parse_tasks_md(content)
        assert tasks == []


class TestParseFeatureFolder:
    """Tests for parse_feature_folder function."""

    def test_parse_feature_folder_all_docs(self, tmp_path: Path):
        """Parse feature folder with all optional docs."""
        from edison.core.import_.speckit import parse_feature_folder

        # Create feature folder structure
        feature_dir = tmp_path / "specs" / "auth-feature"
        feature_dir.mkdir(parents=True)

        (feature_dir / "tasks.md").write_text("- [ ] T001 Create User model")
        (feature_dir / "spec.md").write_text("# Spec")
        (feature_dir / "plan.md").write_text("# Plan")
        (feature_dir / "data-model.md").write_text("# Data Model")
        (feature_dir / "research.md").write_text("# Research")
        contracts_dir = feature_dir / "contracts"
        contracts_dir.mkdir()
        (contracts_dir / "auth.yaml").write_text("openapi: 3.0.0")

        feature = parse_feature_folder(feature_dir)

        assert feature.name == "auth-feature"
        assert feature.path == feature_dir
        assert len(feature.tasks) == 1
        assert feature.has_spec is True
        assert feature.has_plan is True
        assert feature.has_data_model is True
        assert feature.has_contracts is True

    def test_parse_feature_folder_minimal(self, tmp_path: Path):
        """Parse feature folder with only tasks.md."""
        from edison.core.import_.speckit import parse_feature_folder

        feature_dir = tmp_path / "specs" / "simple-feature"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Do something")

        feature = parse_feature_folder(feature_dir)

        assert feature.name == "simple-feature"
        assert len(feature.tasks) == 1
        assert feature.has_spec is False
        assert feature.has_plan is False
        assert feature.has_data_model is False
        assert feature.has_contracts is False

    def test_parse_feature_folder_missing_tasks_md(self, tmp_path: Path):
        """Raise error when tasks.md is missing."""
        from edison.core.import_.speckit import parse_feature_folder, SpecKitImportError

        feature_dir = tmp_path / "specs" / "no-tasks"
        feature_dir.mkdir(parents=True)
        (feature_dir / "plan.md").write_text("# Plan")

        with pytest.raises(SpecKitImportError, match="tasks.md not found"):
            parse_feature_folder(feature_dir)

    def test_parse_feature_folder_from_tasks_md_path(self, tmp_path: Path):
        """Parse feature folder when given path to tasks.md directly."""
        from edison.core.import_.speckit import parse_feature_folder

        feature_dir = tmp_path / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        tasks_file = feature_dir / "tasks.md"
        tasks_file.write_text("- [ ] T001 Create model")

        # Pass path to tasks.md instead of folder
        feature = parse_feature_folder(tasks_file)

        assert feature.name == "auth"
        assert feature.path == feature_dir


# =============================================================================
# GENERATOR TESTS
# =============================================================================


class TestGenerateEdisonTask:
    """Tests for generate_edison_task function."""

    def test_generate_basic_task(self, tmp_path: Path):
        """Generate Edison task from SpecKit task."""
        from edison.core.import_.speckit import (
            parse_feature_folder,
            generate_edison_task,
        )

        # Setup feature folder
        feature_dir = tmp_path / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create User model")

        feature = parse_feature_folder(feature_dir)
        task = generate_edison_task(feature.tasks[0], feature, prefix="auth")

        assert task.id == "auth-T001"
        assert task.title == "Create User model"
        assert "speckit" in task.tags
        assert "auth" in task.tags

    def test_generate_task_with_user_story_tag(self, tmp_path: Path):
        """Generate task with user story tag."""
        from edison.core.import_.speckit import (
            parse_feature_folder,
            generate_edison_task,
        )

        feature_dir = tmp_path / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text(
            "- [ ] T012 [US1] Create User model in src/models/user.py"
        )

        feature = parse_feature_folder(feature_dir)
        task = generate_edison_task(feature.tasks[0], feature, prefix="auth")

        assert task.id == "auth-T012"
        assert "user-story-1" in task.tags

    def test_generate_task_description_contains_links(self, tmp_path: Path):
        """Generated description contains links to spec docs."""
        from edison.core.import_.speckit import (
            parse_feature_folder,
            generate_edison_task,
        )

        feature_dir = tmp_path / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text(
            "- [ ] T001 [US1] Create User model in src/models/user.py"
        )
        (feature_dir / "spec.md").write_text("# Spec")
        (feature_dir / "plan.md").write_text("# Plan")
        (feature_dir / "data-model.md").write_text("# Data Model")

        feature = parse_feature_folder(feature_dir)
        task = generate_edison_task(feature.tasks[0], feature, prefix="auth")

        # Check description contains links
        assert "specs/auth/spec.md" in task.description
        assert "specs/auth/plan.md" in task.description
        assert "specs/auth/data-model.md" in task.description
        assert "User Story US1" in task.description
        assert "src/models/user.py" in task.description


class TestGenerateTaskDescription:
    """Tests for generate_task_description function."""

    def test_description_format_with_all_docs(self, tmp_path: Path):
        """Description includes all available doc links."""
        from edison.core.import_.speckit import (
            parse_feature_folder,
            generate_task_description,
            SpecKitTask,
        )

        feature_dir = tmp_path / "specs" / "payment"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Test")
        (feature_dir / "spec.md").write_text("# Spec")
        (feature_dir / "plan.md").write_text("# Plan")
        (feature_dir / "data-model.md").write_text("# Data Model")
        contracts_dir = feature_dir / "contracts"
        contracts_dir.mkdir()
        (contracts_dir / "api.yaml").write_text("openapi: 3.0.0")

        feature = parse_feature_folder(feature_dir)
        task = SpecKitTask(
            id="T012",
            parallel=True,
            user_story="US2",
            description="Create PaymentService in src/services/payment.py",
            target_file="src/services/payment.py",
            phase="user-story-2",
            completed=False,
        )

        description = generate_task_description(task, feature)

        # Check structure
        assert "**SpecKit Source**:" in description
        assert "specs/payment/tasks.md" in description
        assert "T012" in description
        assert "**Feature**: payment" in description
        assert "**Parallelizable**: Yes" in description
        assert "**User Story**: US2" in description
        assert "## Implementation Target" in description
        assert "`src/services/payment.py`" in description
        assert "## Required Reading" in description
        assert "specs/payment/spec.md" in description
        assert "specs/payment/plan.md" in description
        assert "specs/payment/data-model.md" in description
        assert "specs/payment/contracts/" in description
        assert "## Original SpecKit Task" in description

    def test_description_format_minimal_docs(self, tmp_path: Path):
        """Description handles missing optional docs."""
        from edison.core.import_.speckit import (
            parse_feature_folder,
            generate_task_description,
            SpecKitTask,
        )

        feature_dir = tmp_path / "specs" / "simple"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Test")

        feature = parse_feature_folder(feature_dir)
        task = SpecKitTask(
            id="T001",
            parallel=False,
            user_story=None,
            description="Create something",
            target_file=None,
            phase="setup",
            completed=False,
        )

        description = generate_task_description(task, feature)

        # Should not include links to missing docs
        assert "spec.md" not in description
        assert "plan.md" not in description
        assert "data-model.md" not in description
        assert "contracts/" not in description
        # Should still have basic structure
        assert "**SpecKit Source**:" in description
        assert "## Original SpecKit Task" in description


# =============================================================================
# SYNC TESTS
# =============================================================================


class TestSyncSpecKitFeature:
    """Tests for sync_speckit_feature function."""

    @pytest.fixture
    def repo_env(self, tmp_path: Path, monkeypatch):
        """Setup repository environment for sync tests."""
        from tests.helpers.fixtures import create_repo_with_git
        from tests.helpers.io_utils import write_yaml

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
                            "done": {"allowed_transitions": [{"to": "validated"}]},
                            "validated": {"allowed_transitions": []},
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
                    "task": {"todo": "todo", "wip": "wip", "done": "done", "validated": "validated"},
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

        # Create tasks directories
        (repo / ".project" / "tasks" / "todo").mkdir(parents=True)
        (repo / ".project" / "tasks" / "wip").mkdir(parents=True)
        (repo / ".project" / "tasks" / "done").mkdir(parents=True)
        (repo / ".project" / "qa" / "waiting").mkdir(parents=True)

        monkeypatch.chdir(repo)
        return repo

    def test_sync_creates_new_tasks(self, repo_env: Path):
        """First sync creates all tasks from SpecKit."""
        from edison.core.import_.speckit import sync_speckit_feature, parse_feature_folder

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

        feature = parse_feature_folder(feature_dir)
        result = sync_speckit_feature(feature, prefix="auth", project_root=repo_env)

        assert len(result.created) == 2
        assert "auth-T001" in result.created
        assert "auth-T002" in result.created
        assert len(result.updated) == 0
        assert len(result.flagged) == 0

        # Verify files created
        task_dir = repo_env / ".project" / "tasks" / "todo"
        assert (task_dir / "auth-T001.md").exists()
        assert (task_dir / "auth-T002.md").exists()

    def test_sync_updates_existing_tasks(self, repo_env: Path):
        """Re-sync updates task metadata when changed."""
        from edison.core.import_.speckit import sync_speckit_feature, parse_feature_folder

        # Create SpecKit feature
        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create User model")

        # First sync
        feature = parse_feature_folder(feature_dir)
        sync_speckit_feature(feature, prefix="auth", project_root=repo_env)

        # Modify task description
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create User model with validation")

        # Re-sync
        feature = parse_feature_folder(feature_dir)
        result = sync_speckit_feature(feature, prefix="auth", project_root=repo_env)

        assert len(result.created) == 0
        assert len(result.updated) == 1
        assert "auth-T001" in result.updated

    def test_sync_preserves_edison_state(self, repo_env: Path):
        """Sync preserves Edison task state (wip, done)."""
        from edison.core.import_.speckit import sync_speckit_feature, parse_feature_folder
        from edison.core.task.repository import TaskRepository

        # Create SpecKit feature and sync
        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create User model")

        feature = parse_feature_folder(feature_dir)
        sync_speckit_feature(feature, prefix="auth", project_root=repo_env)

        # Move task to wip state manually
        task_repo = TaskRepository(repo_env)
        task = task_repo.get("auth-T001")
        task_file = repo_env / ".project" / "tasks" / "todo" / "auth-T001.md"
        wip_file = repo_env / ".project" / "tasks" / "wip" / "auth-T001.md"
        task_file.rename(wip_file)

        # Re-sync - should not reset to todo
        feature = parse_feature_folder(feature_dir)
        result = sync_speckit_feature(feature, prefix="auth", project_root=repo_env)

        # Task should be in skipped (state preserved)
        assert "auth-T001" in result.skipped or "auth-T001" in result.updated
        # File should still be in wip
        assert wip_file.exists()
        assert not task_file.exists()

    def test_sync_flags_removed_tasks(self, repo_env: Path):
        """Sync flags tasks removed from SpecKit."""
        from edison.core.import_.speckit import sync_speckit_feature, parse_feature_folder
        from edison.core.task.repository import TaskRepository

        # Create SpecKit feature with 2 tasks
        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text(
            """
- [ ] T001 Task one
- [ ] T002 Task two
"""
        )

        feature = parse_feature_folder(feature_dir)
        sync_speckit_feature(feature, prefix="auth", project_root=repo_env)

        # Remove T002 from SpecKit
        (feature_dir / "tasks.md").write_text("- [ ] T001 Task one")

        # Re-sync
        feature = parse_feature_folder(feature_dir)
        result = sync_speckit_feature(feature, prefix="auth", project_root=repo_env)

        assert "auth-T002" in result.flagged

        # Verify task has removed-from-spec tag
        task_repo = TaskRepository(repo_env)
        task = task_repo.get("auth-T002")
        assert task is not None
        assert "removed-from-spec" in task.tags

    def test_sync_adds_new_tasks(self, repo_env: Path):
        """Sync adds new tasks from updated SpecKit."""
        from edison.core.import_.speckit import sync_speckit_feature, parse_feature_folder

        # Create SpecKit feature with 1 task
        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Task one")

        feature = parse_feature_folder(feature_dir)
        sync_speckit_feature(feature, prefix="auth", project_root=repo_env)

        # Add T002 to SpecKit
        (feature_dir / "tasks.md").write_text(
            """
- [ ] T001 Task one
- [ ] T002 New task
"""
        )

        # Re-sync
        feature = parse_feature_folder(feature_dir)
        result = sync_speckit_feature(feature, prefix="auth", project_root=repo_env)

        assert len(result.created) == 1
        assert "auth-T002" in result.created

    def test_sync_dry_run_no_changes(self, repo_env: Path):
        """Dry run shows changes without writing."""
        from edison.core.import_.speckit import sync_speckit_feature, parse_feature_folder

        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create User model")

        feature = parse_feature_folder(feature_dir)
        result = sync_speckit_feature(feature, prefix="auth", project_root=repo_env, dry_run=True)

        assert len(result.created) == 1
        assert "auth-T001" in result.created

        # Verify no files created
        task_dir = repo_env / ".project" / "tasks" / "todo"
        assert not (task_dir / "auth-T001.md").exists()

    def test_sync_creates_qa_records(self, repo_env: Path):
        """Sync creates QA records when create_qa=True."""
        from edison.core.import_.speckit import sync_speckit_feature, parse_feature_folder
        from edison.core.qa.workflow.repository import QARepository

        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create User model")

        feature = parse_feature_folder(feature_dir)
        sync_speckit_feature(feature, prefix="auth", project_root=repo_env, create_qa=True)

        # Verify QA record created
        qa_repo = QARepository(repo_env)
        qa = qa_repo.get("auth-T001-qa")
        assert qa is not None

    def test_sync_no_qa_records_when_disabled(self, repo_env: Path):
        """Sync skips QA records when create_qa=False."""
        from edison.core.import_.speckit import sync_speckit_feature, parse_feature_folder

        feature_dir = repo_env / "specs" / "auth"
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text("- [ ] T001 Create User model")

        feature = parse_feature_folder(feature_dir)
        sync_speckit_feature(feature, prefix="auth", project_root=repo_env, create_qa=False)

        # Verify no QA record
        qa_dir = repo_env / ".project" / "qa" / "waiting"
        assert not (qa_dir / "auth-T001-qa.md").exists()
