"""Context7 marker validation tests.

Tests for distinguishing "missing" vs "invalid" markers and validating required fields.

TDD: RED phase - Write failing tests first.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from helpers.io_utils import write_yaml
from tests.helpers.cache_utils import reset_all_and_reload
from tests.helpers.env_setup import setup_project_root
from tests.helpers.fixtures import create_repo_with_git


@pytest.fixture
def repo_env(tmp_path: Path, monkeypatch: Any) -> Path:
    """Create a repository with minimal Context7 config for testing."""
    repo = create_repo_with_git(tmp_path)

    # Create .project structure
    (repo / ".project" / "tasks" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "wip").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "done").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "meta").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "waiting").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "wip").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "sessions" / "active").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "TEMPLATE.md").write_text("# TEMPLATE\n", encoding="utf-8")

    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    write_yaml(
        cfg_dir / "tasks.yaml",
        {
            "tasks": {
                "paths": {
                    "root": ".project/tasks",
                    "qaRoot": ".project/qa",
                    "metaRoot": ".project/tasks/meta",
                    "template": ".project/tasks/TEMPLATE.md",
                    "evidenceSubdir": "validation-evidence",
                }
            }
        },
    )

    write_yaml(
        cfg_dir / "workflow.yaml",
        {
            "version": "1.0",
            "statemachine": {
                "task": {
                    "states": {
                        "todo": {"initial": True, "allowed_transitions": ["wip"]},
                        "wip": {"allowed_transitions": ["done"]},
                        "done": {"allowed_transitions": []},
                    }
                },
                "qa": {
                    "states": {
                        "waiting": {"initial": True, "allowed_transitions": ["todo"]},
                        "todo": {"allowed_transitions": ["wip"]},
                        "wip": {"allowed_transitions": ["done"]},
                        "done": {"allowed_transitions": []},
                    }
                },
                "session": {
                    "states": {
                        "active": {"initial": True, "allowed_transitions": []},
                    }
                },
            },
        },
    )

    # Create context7 config with triggers
    write_yaml(
        cfg_dir / "context7.yaml",
        {
            "context7": {
                "triggers": {
                    "fastapi": ["**/*fastapi*", "**/api/**/*.py"],
                    "pytest": ["**/test_*.py", "**/tests/**/*.py"],
                },
                "aliases": {
                    "fastapi": "fastapi",
                },
            }
        },
    )

    setup_project_root(monkeypatch, repo)
    reset_all_and_reload()
    return repo


class TestMarkerValidation:
    """Tests for Context7 marker validation (missing vs invalid)."""

    def test_missing_marker_returns_missing_status(self, repo_env: Path) -> None:
        """When no marker file exists, classify_marker should return 'missing'."""
        from edison.core.qa.context.context7 import classify_marker

        task_id = "test-task-1"
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        result = classify_marker(round_dir, "fastapi")

        assert result["status"] == "missing"
        assert result["package"] == "fastapi"
        assert "path_checked" in result

    def test_valid_marker_returns_valid_status(self, repo_env: Path) -> None:
        """When marker has all required fields, classify_marker returns 'valid'."""
        from edison.core.qa.context.context7 import classify_marker

        task_id = "test-task-2"
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Write a valid marker with required fields
        marker_content = """---
package: fastapi
libraryId: /tiangolo/fastapi
topics:
  - routing
  - middleware
queriedAt: 2025-01-02T10:00:00Z
---

Context7 documentation was queried for fastapi.
"""
        (round_dir / "context7-fastapi.txt").write_text(marker_content, encoding="utf-8")

        result = classify_marker(round_dir, "fastapi")

        assert result["status"] == "valid"
        assert result["package"] == "fastapi"

    def test_invalid_marker_missing_topics_returns_invalid(self, repo_env: Path) -> None:
        """When marker is missing 'topics', classify_marker returns 'invalid'."""
        from edison.core.qa.context.context7 import classify_marker

        task_id = "test-task-3"
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Write marker missing 'topics'
        marker_content = """---
package: fastapi
libraryId: /tiangolo/fastapi
queriedAt: 2025-01-02T10:00:00Z
---

Missing topics field.
"""
        (round_dir / "context7-fastapi.txt").write_text(marker_content, encoding="utf-8")

        result = classify_marker(round_dir, "fastapi")

        assert result["status"] == "invalid"
        assert result["package"] == "fastapi"
        assert "topics" in result.get("missing_fields", [])

    def test_invalid_marker_missing_library_id_returns_invalid(self, repo_env: Path) -> None:
        """When marker is missing 'libraryId', classify_marker returns 'invalid'."""
        from edison.core.qa.context.context7 import classify_marker

        task_id = "test-task-4"
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Write marker missing 'libraryId'
        marker_content = """---
package: fastapi
topics:
  - routing
queriedAt: 2025-01-02T10:00:00Z
---

Missing libraryId field.
"""
        (round_dir / "context7-fastapi.txt").write_text(marker_content, encoding="utf-8")

        result = classify_marker(round_dir, "fastapi")

        assert result["status"] == "invalid"
        assert result["package"] == "fastapi"
        assert "libraryId" in result.get("missing_fields", [])

    def test_invalid_marker_empty_file_returns_invalid(self, repo_env: Path) -> None:
        """When marker file is empty, classify_marker returns 'invalid'."""
        from edison.core.qa.context.context7 import classify_marker

        task_id = "test-task-5"
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Write empty marker
        (round_dir / "context7-fastapi.txt").write_text("", encoding="utf-8")

        result = classify_marker(round_dir, "fastapi")

        assert result["status"] == "invalid"
        assert result["package"] == "fastapi"

    def test_md_extension_also_works(self, repo_env: Path) -> None:
        """Marker with .md extension should also be detected and validated."""
        from edison.core.qa.context.context7 import classify_marker

        task_id = "test-task-6"
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Write valid marker with .md extension
        marker_content = """---
package: pytest
libraryId: /pytest-dev/pytest
topics:
  - fixtures
queriedAt: 2025-01-02T10:00:00Z
---

Context7 docs for pytest.
"""
        (round_dir / "context7-pytest.md").write_text(marker_content, encoding="utf-8")

        result = classify_marker(round_dir, "pytest")

        assert result["status"] == "valid"
        assert result["package"] == "pytest"


class TestClassifyPackages:
    """Tests for classifying multiple packages at once."""

    def test_classify_packages_separates_missing_and_invalid(self, repo_env: Path) -> None:
        """classify_packages should return separate lists for missing/invalid/valid."""
        from edison.core.qa.context.context7 import classify_packages

        task_id = "test-task-7"
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Write valid marker for fastapi
        valid_marker = """---
package: fastapi
libraryId: /tiangolo/fastapi
topics:
  - routing
queriedAt: 2025-01-02T10:00:00Z
---
"""
        (round_dir / "context7-fastapi.txt").write_text(valid_marker, encoding="utf-8")

        # Write invalid marker for pytest (missing topics)
        invalid_marker = """---
package: pytest
libraryId: /pytest-dev/pytest
queriedAt: 2025-01-02T10:00:00Z
---
"""
        (round_dir / "context7-pytest.txt").write_text(invalid_marker, encoding="utf-8")

        # No marker for 'pydantic' - should be missing

        result = classify_packages(round_dir, ["fastapi", "pytest", "pydantic"])

        assert "pydantic" in result["missing"]
        assert any(p["package"] == "pytest" for p in result["invalid"])
        assert "fastapi" in result["valid"]

    def test_classify_packages_returns_evidence_directory(self, repo_env: Path) -> None:
        """classify_packages should include the evidence directory in output."""
        from edison.core.qa.context.context7 import classify_packages

        task_id = "test-task-8"
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        result = classify_packages(round_dir, ["fastapi"])

        assert "evidence_dir" in result
        assert result["evidence_dir"] == str(round_dir)


class TestMissingPackagesEnhanced:
    """Tests for enhanced missing_packages function with invalid marker support."""

    def test_missing_packages_with_invalid_markers(self, repo_env: Path) -> None:
        """missing_packages_detailed should return both missing and invalid packages."""
        from edison.core.qa.context.context7 import missing_packages_detailed

        task_id = "test-task-9"
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Create implementation report to establish round
        impl_content = """---
filesChanged:
  - src/api/main.py
---
Implementation report.
"""
        (round_dir / "implementation-report.md").write_text(impl_content, encoding="utf-8")

        # Write invalid marker
        invalid_marker = """---
package: fastapi
queriedAt: 2025-01-02T10:00:00Z
---
"""
        (round_dir / "context7-fastapi.txt").write_text(invalid_marker, encoding="utf-8")

        result = missing_packages_detailed(task_id, ["fastapi", "pytest"])

        assert "pytest" in result["missing"]
        assert any(p["package"] == "fastapi" for p in result["invalid"])
        assert "evidence_dir" in result
