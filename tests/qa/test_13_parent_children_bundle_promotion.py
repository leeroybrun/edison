from __future__ import annotations

import json
from pathlib import Path
import pytest

from helpers.command_runner import run_script, assert_command_success
from helpers.assertions import assert_file_exists
from helpers.test_env import TestProjectDir


@pytest.mark.integration
def test_parent_children_bundle_promotion(test_project_dir: TestProjectDir):
    """End-to-end: parent + children bundle; child QAs promote via parent bundle."""
    sid = "test-bundle-promo"
    parent = "910-wave1-parent"
    children = ["910.1-wave1-ui", "910.2-wave1-api"]

    # Create session + parent + children
    test_project_dir.create_session(sid, state="wip")
    # Create tasks via helper
    test_project_dir.create_task(parent, wave="wave1", slug="parent", state="todo")
    for cid in children:
        num, wave, slug = cid.split("-", 2)
        test_project_dir.create_task(cid, wave=wave, slug=slug, state="todo")
        assert_command_success(run_script("tasks/link", [parent, cid, "--session", sid], cwd=test_project_dir.tmp_path))

    # Evidence + reports for each task (global + critical validators approve)
    vids = [("codex-global", "codex"), ("claude-global", "claude"), ("security", "codex"), ("performance", "codex")]
    tasks = [parent, *children]
    for tid in tasks:
        rd = test_project_dir.project_root / "qa" / "validation-evidence" / tid / "round-1"
        rd.mkdir(parents=True, exist_ok=True)
        # Implementation report + command artefacts (for tasks/ready invariants)
        impl = {
            "taskId": tid,
            "round": 1,
            "implementationApproach": "orchestrator-direct",
            "primaryModel": "codex",
            "completionStatus": "complete",
            "followUpTasks": [],
            "notesForValidator": "ok",
            "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:10:00Z"}
        }
        (rd / "implementation-report.json").write_text(json.dumps(impl))
        for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
            (rd / name).write_text("Exit code: 0\n")
        # Context7 markers to satisfy enforcement when diff implies packages
        for pkg in ("next", "zod"):
            (rd / f"context7-{pkg}.txt").write_text(f"Context7 refreshed: {pkg}\n")
        # Validator reports
        for vid, model in vids:
            report = {
                "taskId": tid,
                "round": 1,
                "validatorId": vid,
                "model": model,
                "verdict": "approve",
                "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:05:00Z"}
            }
            (rd / f"validator-{vid}-report.json").write_text(json.dumps(report))

    # Create QAs (session-scoped)
    assert_command_success(run_script("qa/new", [parent, "--session", sid], cwd=test_project_dir.tmp_path))
    for cid in children:
        assert_command_success(run_script("qa/new", [cid, "--session", sid], cwd=test_project_dir.tmp_path))

    # Ready + done for children
    for cid in children:
        # Write child task under tasks/done to satisfy guards
        done = test_project_dir.project_root / "tasks" / "done" / f"{cid}.md"
        done.parent.mkdir(parents=True, exist_ok=True)
        done.write_text("\n".join([f"# Task {cid}", "", "- **Status:** done"]) + "\n")
        try:
            (test_project_dir.project_root / "tasks" / "todo" / f"{cid}.md").unlink()
        except FileNotFoundError:
            pass

    # Move parent to done (children are done; evidence present)
    done = test_project_dir.project_root / "tasks" / "done" / f"{parent}.md"
    done.parent.mkdir(parents=True, exist_ok=True)
    done.write_text("\n".join([f"# Task {parent}", "", "- **Status:** done"]) + "\n")
    try:
        (test_project_dir.project_root / "tasks" / "todo" / f"{parent}.md").unlink()
    except FileNotFoundError:
        pass

    # Write bundle-approved.json directly (simulating validators/validate approval)
    evdir = test_project_dir.project_root / "qa" / "validation-evidence" / parent / "round-1"
    evdir.mkdir(parents=True, exist_ok=True)
    (evdir / "bundle-approved.json").write_text(json.dumps({"approved": True}, indent=2))
    # Promote parent QA waiting→todo→wip (done requires full validator suite; covered elsewhere)
    assert_command_success(run_script("qa/promote", ["--task", parent, "--to", "todo", "--session", sid], cwd=test_project_dir.tmp_path))
    assert_command_success(run_script("qa/promote", ["--task", parent, "--to", "wip", "--session", sid], cwd=test_project_dir.tmp_path))
    # Promote child QAs waiting→todo→wip (uses parent bundle to decide)
    for cid in children:
        assert_command_success(run_script("qa/promote", ["--task", cid, "--to", "todo", "--session", sid], cwd=test_project_dir.tmp_path))
        assert_command_success(run_script("qa/promote", ["--task", cid, "--to", "wip", "--session", sid], cwd=test_project_dir.tmp_path))

    # Assert evidence & outputs exist
    bundle_summary = test_project_dir.project_root / "qa" / "validation-evidence" / parent / "round-1" / "bundle-approved.json"
    assert_file_exists(bundle_summary)
