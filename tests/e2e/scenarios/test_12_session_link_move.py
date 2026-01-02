from __future__ import annotations

import pytest
from pathlib import Path

from helpers.command_runner import run_script, assert_command_success
from helpers.assertions import assert_file_exists
from helpers.env import TestProjectDir
from edison.core.utils.text import parse_frontmatter


@pytest.mark.integration
def test_link_moves_tasks_into_session(project_dir: TestProjectDir):
    session_id = "test-link-move"
    parent_id = "900-wave1-parent"
    child_id = "900.1-wave1-child"

    # Create session
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path))

    # Create tasks globally (no --session)
    assert_command_success(run_script("tasks/new", ["--id", "900", "--wave", "wave1", "--slug", "parent"], cwd=project_dir.tmp_path))
    assert_command_success(run_script("tasks/new", ["--id", "900.1", "--wave", "wave1", "--slug", "child"], cwd=project_dir.tmp_path))

    # Link in session; should relocate both into session tree preserving status (todo)
    assert_command_success(run_script("tasks/link", [parent_id, child_id, "--session", session_id], cwd=project_dir.tmp_path))

    # Links are stored in task entities (YAML frontmatter); tasks remain in the global task tree.
    parent_path = project_dir.project_root / "tasks" / "todo" / f"{parent_id}.md"
    child_path = project_dir.project_root / "tasks" / "todo" / f"{child_id}.md"
    assert_file_exists(parent_path)
    assert_file_exists(child_path)

    parent_doc = parse_frontmatter(parent_path.read_text(encoding="utf-8"))
    child_doc = parse_frontmatter(child_path.read_text(encoding="utf-8"))
    assert child_id in ((parent_doc.frontmatter or {}).get("child_ids") or [])
    assert (child_doc.frontmatter or {}).get("parent_id") == parent_id
