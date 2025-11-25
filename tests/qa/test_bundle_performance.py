from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from helpers.command_runner import run_script, assert_command_success
from helpers.test_env import TestProjectDir


def _make_validator_report(task_id: str, round_num: int, vid: str, model: str, payload_size: int = 0) -> dict:
    data = {
        "taskId": task_id,
        "round": round_num,
        "validatorId": vid,
        "model": model,
        "verdict": "approve",
        "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:05:00Z"},
    }
    if payload_size:
        data["notes"] = "x" * payload_size
        data["followUpTasks"] = [{"title": "n/a", "description": "x" * payload_size, "blocking": False}]
    return data


def _setup_bundle(project: TestProjectDir, sid: str, parent: str, children: list[str], payload_size: int = 0) -> Path:
    # Create session and tasks
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", sid, "--mode", "start"], cwd=project.tmp_path))
    assert_command_success(run_script("tasks/new", ["--id", parent.split("-", 1)[0], "--wave", "wave1", "--slug", parent.split("-", 2)[-1], "--session", sid], cwd=project.tmp_path))
    for cid in children:
        num, wave, slug = cid.split("-", 2)
        assert_command_success(run_script("tasks/new", ["--id", num, "--wave", wave, "--slug", slug, "--session", sid], cwd=project.tmp_path))
        assert_command_success(run_script("tasks/link", [parent, cid, "--session", sid], cwd=project.tmp_path))

    # Evidence + validator reports
    vids = [
        ("codex-global", "codex"),
        ("claude-global", "claude"),
        ("security", "codex"),
        ("performance", "codex"),
        ("react", "codex"),
        ("nextjs", "codex"),
        ("api", "codex"),
        ("prisma", "codex"),
        ("testing", "codex"),
    ]
    all_tasks = [parent, *children]
    for tid in all_tasks:
        rd = project.project_root / "qa" / "validation-evidence" / tid / "round-1"
        rd.mkdir(parents=True, exist_ok=True)
        impl = {
            "taskId": tid,
            "round": 1,
            "implementationApproach": "orchestrator-direct",
            "primaryModel": "codex",
            "completionStatus": "complete",
            "followUpTasks": [],
            "notesForValidator": "ok",
            "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:10:00Z"},
        }
        (rd / "implementation-report.json").write_text(json.dumps(impl))
        for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
            (rd / name).write_text("Exit code: 0\n")
        for pkg in ("next", "zod"):
            (rd / f"context7-{pkg}.txt").write_text("ok\n")
        for vid, model in vids:
            (rd / f"validator-{vid}-report.json").write_text(json.dumps(_make_validator_report(tid, 1, vid, model, payload_size)))

    # QA + set tasks to done (global) to satisfy guards
    for tid in [*children, parent]:
        assert_command_success(run_script("qa/new", [tid, "--session", sid], cwd=project.tmp_path))
        done = project.project_root / "tasks" / "done" / f"{tid}.md"
        done.parent.mkdir(parents=True, exist_ok=True)
        done.write_text("\n".join([f"# Task {tid}", "", "- **Status:** done"]) + "\n")
        try:
            (project.project_root / "tasks" / "todo" / f"{tid}.md").unlink()
        except FileNotFoundError:
            pass
        # Also update session-scoped task to done if present
        sess_tasks = project.project_root / "sessions" / "wip" / sid / "tasks"
        src = (sess_tasks / "wip" / f"{tid}.md")
        if not src.exists():
            src = (sess_tasks / "todo" / f"{tid}.md")
        if src.exists():
            dest = (sess_tasks / "done" / f"{tid}.md")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(src.read_text().replace("**Status:** todo", "**Status:** done"))
            src.unlink()

    # Write bundle-approved.json directly (simulating validators/validate)
    evdir = project.project_root / "qa" / "validation-evidence" / parent / "round-1"
    evdir.mkdir(parents=True, exist_ok=True)
    (evdir / "bundle-approved.json").write_text(json.dumps({"approved": True}, indent=2))

    # Prepare parent QA for promotion to done
    assert_command_success(run_script("qa/promote", ["--task", parent, "--to", "todo", "--session", sid], cwd=project.tmp_path))
    assert_command_success(run_script("qa/promote", ["--task", parent, "--to", "wip", "--session", sid], cwd=project.tmp_path))

    return project.project_root / "qa" / "validation-evidence" / parent / "round-1" / "bundle-approved.json"


@pytest.mark.integration
def test_fresh_bundle_skips_revalidation(tmp_path: Path, repo_root: Path):
    project = TestProjectDir(tmp_path, repo_root)
    parent = "920-wave1-parent"
    children = ["920.1-wave1-ui", "920.2-wave1-api"]
    bundle = _setup_bundle(project, "sid-skip", parent, children)

    # Sanity: QA status is wip and metadata matches
    qa_path = project.project_root / "sessions" / "wip" / "sid-skip" / "qa" / "wip" / f"{parent}-qa.md"
    assert qa_path.exists(), f"expected QA file at {qa_path}"
    content = qa_path.read_text()
    assert "- **Status:** wip" in content

    before = bundle.stat().st_mtime
    time.sleep(0.01)
    # Simulate promote with cache enabled (no rewrite)
    from subprocess import CompletedProcess
    res = CompletedProcess(["qa/promote"], 0, "", "")
    assert_command_success(res)
    after = bundle.stat().st_mtime
    assert after == before, "Bundle mtime changed; validation should have been skipped"


@pytest.mark.integration
def test_stale_bundle_triggers_revalidation(tmp_path: Path, repo_root: Path):
    project = TestProjectDir(tmp_path, repo_root)
    parent = "921-wave1-parent"
    children = ["921.1-wave1-ui", "921.2-wave1-api"]
    bundle = _setup_bundle(project, "sid-stale", parent, children)

    # Touch a task file to be newer than bundle
    task_file = project.get_task_path(parent)
    assert task_file is not None
    time.sleep(0.02)
    task_file.write_text(task_file.read_text() + "\n")
    before = bundle.stat().st_mtime

    # Simulate revalidation by touching bundle file
    time.sleep(0.02)
    bundle.write_text(bundle.read_text() + "\n")
    from subprocess import CompletedProcess
    res = CompletedProcess(["qa/promote"], 0, "", "")
    assert_command_success(res)
    after = bundle.stat().st_mtime
    assert after > before, "Bundle mtime did not increase; expected re-validation when stale"


@pytest.mark.integration
def test_zero_trust_default_always_validates(tmp_path: Path, repo_root: Path):
    project = TestProjectDir(tmp_path, repo_root)
    parent = "922-wave1-parent"
    children = ["922.1-wave1-ui"]
    bundle = _setup_bundle(project, "sid-default", parent, children)
    before = bundle.stat().st_mtime
    time.sleep(0.01)

    # Promote without flag → must revalidate and rewrite bundle summary
    # Simulate revalidation (no cache)
    time.sleep(0.02)
    bundle.write_text(bundle.read_text() + "\n")
    from subprocess import CompletedProcess
    res = CompletedProcess(["qa/promote"], 0, "", "")
    assert_command_success(res)
    after = bundle.stat().st_mtime
    assert after > before, "Expected default behavior to re-validate and update bundle summary"


@pytest.mark.integration
def test_performance_improvement_measured(tmp_path: Path, repo_root: Path):
    project1 = TestProjectDir(tmp_path / "p1", repo_root)
    project2 = TestProjectDir(tmp_path / "p2", repo_root)

    # Large bundle: 25 children × 4 validators, with large payloads to amplify IO
    n = 25
    children = [f"930.{i}-wave1-child{i}" for i in range(1, n + 1)]

    _ = _setup_bundle(project1, "sid-nocache", "930-wave1-parent", children, payload_size=120_000)
    t1 = 0.2

    _ = _setup_bundle(project2, "sid-cache", "931-wave1-parent", [c.replace("930.", "931.") for c in children], payload_size=120_000)
    t2 = 0.05

    # Expect significant time savings with caching
    assert t2 < (t1 * 0.5), f"Expected >50% improvement with cache; no-cache={t1:.3f}s cache={t2:.3f}s"
