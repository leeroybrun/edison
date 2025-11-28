"""Test that TestProjectDir creates fallback templates when repo templates don't exist.

This test ensures the fix for missing TEMPLATE.md files is working correctly.
TestProjectDir should create minimal fallback templates when the repo root doesn't
contain .project/tasks/TEMPLATE.md or .project/qa/TEMPLATE.md files.
"""
from __future__ import annotations

from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from helpers.env import TestProjectDir


def test_testprojectdir_creates_fallback_templates(tmp_path: Path):
    """TestProjectDir creates fallback templates when repo templates are missing."""
    # Create a fake repo_root without templates
    fake_repo_root = tmp_path / "fake_repo"
    fake_repo_root.mkdir()
    (fake_repo_root / ".project").mkdir()
    (fake_repo_root / ".project" / "tasks").mkdir()
    (fake_repo_root / ".project" / "qa").mkdir()
    # Intentionally DO NOT create TEMPLATE.md files

    # Create TestProjectDir
    test_dir = tmp_path / "test_env"
    test_dir.mkdir()
    proj = TestProjectDir(test_dir, fake_repo_root)

    # Verify task template was created (with fallback)
    task_template = proj.project_root / "tasks" / "TEMPLATE.md"
    assert task_template.exists(), f"Task TEMPLATE.md should exist at {task_template}"

    task_content = task_template.read_text()
    assert "Task" in task_content or "task" in task_content
    assert "Status" in task_content

    # Verify QA template was created (with fallback)
    qa_template = proj.project_root / "qa" / "TEMPLATE.md"
    assert qa_template.exists(), f"QA TEMPLATE.md should exist at {qa_template}"

    qa_content = qa_template.read_text()
    assert "Validator" in qa_content
    assert "Status" in qa_content


def test_testprojectdir_uses_repo_templates_when_available(tmp_path: Path):
    """TestProjectDir uses repo templates when they exist (doesn't use fallback)."""
    # Create a fake repo_root WITH custom templates
    fake_repo_root = tmp_path / "fake_repo"
    fake_repo_root.mkdir()
    (fake_repo_root / ".project" / "tasks").mkdir(parents=True)
    (fake_repo_root / ".project" / "qa").mkdir(parents=True)

    task_template_content = "# CUSTOM TASK TEMPLATE\n**Status:** custom\n"
    qa_template_content = "# CUSTOM QA TEMPLATE\n**Validator:** custom\n"

    (fake_repo_root / ".project" / "tasks" / "TEMPLATE.md").write_text(task_template_content)
    (fake_repo_root / ".project" / "qa" / "TEMPLATE.md").write_text(qa_template_content)

    # Create TestProjectDir
    test_dir = tmp_path / "test_env"
    test_dir.mkdir()
    proj = TestProjectDir(test_dir, fake_repo_root)

    # Verify custom templates were copied (not fallback)
    task_template = proj.project_root / "tasks" / "TEMPLATE.md"
    qa_template = proj.project_root / "qa" / "TEMPLATE.md"

    assert task_template.read_text() == task_template_content
    assert qa_template.read_text() == qa_template_content
