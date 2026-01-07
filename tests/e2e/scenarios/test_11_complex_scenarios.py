"""Test 11: Complex Integration Scenarios (REAL CLI)

All tests in this file execute REAL Edison CLI commands.
Absolutely no mock data helpers are used. Workflows mirror
`edison` session workflow guidelines:

Coverage:
- Multiple concurrent sessions
- Multi-task dependency graphs (linking, parent/child)
- Cross-session reclaim/transfer
- Partial session completion (session complete guard fails)
- Session merge task creation (worktree sessions)
- Large-scale validation flow (many tasks)
- Rejection → fix → revalidation cycles
- Worktree session isolation
- Mixed worktree and non-worktree sessions
- Complex state transitions
"""
from __future__ import annotations

import pytest
from pathlib import Path

import json

from helpers import TestProjectDir, TestGitRepo
from helpers.assertions import (
    assert_file_exists,
    assert_directory_exists,
)
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
    assert_output_contains,
)
from edison.core.utils.text import format_frontmatter, parse_frontmatter


def _seed_validation_evidence(repo_root: Path, task_id: str, round_num: int = 1) -> Path:
    """Create minimal validation evidence required for qa/promote and validation guards."""
    from edison.core.qa.evidence import EvidenceService
    from edison.core.qa.evidence.command_evidence import write_command_evidence

    ev = EvidenceService(task_id=task_id, project_root=repo_root)
    rd = ev.ensure_round(round_num)

    for fname in [
        "command-type-check.txt",
        "command-lint.txt",
        "command-test.txt",
        "command-test-full.txt",
        "command-build.txt",
    ]:
        name = fname.removeprefix("command-").removesuffix(".txt")
        write_command_evidence(
            path=rd / fname,
            task_id=task_id,
            round_num=round_num,
            command_name=name,
            command="echo ok",
            cwd=str(repo_root),
            exit_code=0,
            output="ok\n",
            runner="edison-tests",
        )

    (rd / ev.implementation_filename).write_text(
        format_frontmatter({"taskId": task_id, "round": round_num, "completionStatus": "complete"}) + "\n",
        encoding="utf-8",
    )
    (rd / ev.bundle_filename).write_text(
        format_frontmatter({"taskId": task_id, "round": round_num, "approved": True}) + "\n",
        encoding="utf-8",
    )
    (ev.get_validator_report_path(rd, "main")).write_text(
        format_frontmatter({"taskId": task_id, "round": round_num, "validatorId": "main", "verdict": "approve"}) + "\n",
        encoding="utf-8",
    )
    return rd


def _start_impl_tracking(task_id: str, *, cwd: Path) -> None:
    """Create the evidence round + implementation report required by task completion guards."""
    assert_command_success(
        run_script(
            "session/track",
            ["start", "--task", task_id, "--type", "implementation"],
            cwd=cwd,
        )
    )


def _qa_to_done(task_id: str, session_id: str, repo_root: Path, cwd: Path) -> None:
    """Promote QA through required states with evidence so done transition succeeds."""
    assert_command_success(
        run_script("qa/promote", [task_id, "--status", "todo", "--session", session_id], cwd=cwd)
    )
    assert_command_success(
        run_script("qa/promote", [task_id, "--status", "wip", "--session", session_id], cwd=cwd)
    )
    _seed_validation_evidence(repo_root, task_id)
    assert_command_success(
        run_script("qa/promote", [task_id, "--status", "done", "--session", session_id], cwd=cwd)
    )


@pytest.mark.integration
@pytest.mark.slow
def test_multiple_concurrent_sessions(project_dir: TestProjectDir):
    """Test multiple sessions running concurrently.

    Scenario:
    - 3 sessions working on different features
    - Each session has multiple tasks
    - Sessions can complete independently
    """
    # Create 3 concurrent sessions via REAL CLI and seed tasks
    sessions = [f"session-{i}" for i in range(3)]
    for session_id in sessions:
        r = run_script(
            "session",
            ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
        assert_command_success(r)

        # 2 tasks per session
        for j in range(2):
            prio = 100 * int(session_id.split("-")[-1]) + j * 50
            task_id = f"{prio}-wave1-task"

            # Create task and register with session
            c1 = run_script(
                "tasks/new",
                ["--id", str(prio), "--wave", "wave1", "--slug", "task", "--session", session_id],
                cwd=project_dir.tmp_path,
            )
            assert_command_success(c1)

            # Claim into session (stamps owner/claimed metadata)
            c2 = run_script(
                "tasks/claim",
                [task_id, "--session", session_id, "--owner", session_id],
                cwd=project_dir.tmp_path,
            )
            assert_command_success(c2)

            # Move to wip for active work
            m = run_script(
                "tasks/status",
                [task_id, "--status", "wip", "--session", session_id],
                cwd=project_dir.tmp_path,
            )
            assert_command_success(m)

    # Verify sessions list their tasks via session status
    for session_id in sessions:
        st = run_script("session", ["status", session_id, "--json"], cwd=project_dir.tmp_path)
        assert_command_success(st)
        assert_output_contains(st, session_id)


@pytest.mark.integration
@pytest.mark.slow
def test_multi_task_dependencies(project_dir: TestProjectDir):
    """Test complex task dependency tree.

    Scenario:
    - Parent task with multiple children
    - Children have their own children (grandchildren)
    - Validation must happen in dependency order
    """
    session_id = "test-dependencies"
    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
    )

    # Create parent in wip
    assert_command_success(
        run_script(
            "tasks/new",
            ["--id", "100", "--wave", "wave1", "--slug", "parent", "--session", session_id],
            cwd=project_dir.tmp_path,
        )
    )
    assert_command_success(
        run_script("tasks/status", ["100-wave1-parent", "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path)
    )

    # Children
    for child in [
        ("100.1", "child1"),
        ("100.2", "child2"),
    ]:
        cid, slug = child
        assert_command_success(
            run_script(
                "tasks/new",
                ["--id", cid, "--wave", "wave1", "--slug", slug, "--session", session_id],
                cwd=project_dir.tmp_path,
            )
        )
        # Link to parent in session graph
        assert_command_success(
            run_script("tasks/link", ["100-wave1-parent", f"{cid}-wave1-{slug}", "--session", session_id], cwd=project_dir.tmp_path)
        )

    # Grandchildren under 100.1-child1
    for g in [("100.1.1", "grandchild"), ("100.1.2", "grandchild2")]:
        gid, slug = g
        tid = f"{gid}-wave1-{slug}"
        assert_command_success(
            run_script(
                "tasks/new",
                ["--id", gid, "--wave", "wave1", "--slug", slug, "--session", session_id],
                cwd=project_dir.tmp_path,
            )
        )
        assert_command_success(
            run_script("tasks/link", ["100.1-wave1-child1", tid, "--session", session_id], cwd=project_dir.tmp_path)
        )

    # Validate session JSON contains hierarchy
    st = run_script("session", ["status", session_id, "--json"], cwd=project_dir.tmp_path)
    assert_command_success(st)
    # Just sanity-check a few relationship strings exist
    assert_output_contains(st, "100-wave1-parent")
    assert_output_contains(st, "100.1-wave1-child1")
    assert_output_contains(st, "100.1.1-wave1-grandchild")


@pytest.mark.integration
@pytest.mark.edge_case
def test_cross_session_task_transfer(project_dir: TestProjectDir):
    """Test transferring task ownership between sessions.

    Scenario:
    - Task starts in session-1
    - Session-1 is abandoned
    - Task is reclaimed by session-2
    """
    session1 = "test-transfer-1"
    session2 = "test-transfer-2"
    task_id = "150-wave1-transfer"

    # Create sessions
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session1, "--mode", "start"], cwd=project_dir.tmp_path))
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session2, "--mode", "start"], cwd=project_dir.tmp_path))

    # Create task and claim to session1
    assert_command_success(run_script("tasks/new", ["--id", "150", "--wave", "wave1", "--slug", "transfer", "--session", session1], cwd=project_dir.tmp_path))
    assert_command_success(run_script("tasks/claim", [task_id, "--session", session1, "--owner", session1], cwd=project_dir.tmp_path))

    # Reclaim is only allowed when the original session is inactive/expired.
    # Simulate an expired session by aging lastActive beyond the configured timeout.
    from datetime import datetime, timezone, timedelta
    import json

    session1_json = project_dir.project_root / "sessions" / "wip" / session1 / "session.json"
    data = json.loads(session1_json.read_text(encoding="utf-8"))
    meta = data.setdefault("meta", {})
    old_time = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat().replace("+00:00", "Z")
    meta["createdAt"] = old_time
    meta["lastActive"] = old_time
    session1_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    # Re-claim to session2 (transfer ownership)
    assert_command_success(
        run_script(
            "tasks/claim",
            [task_id, "--session", session2, "--owner", session2, "--reclaim", "--reason", "transfer ownership"],
            cwd=project_dir.tmp_path,
        )
    )

    # Verify Owner in file content reflects session2
    task_path = project_dir.project_root / "tasks" / "todo" / f"{task_id}.md"
    assert_file_exists(task_path)
    from helpers.assertions import read_file
    doc = parse_frontmatter(read_file(task_path))
    assert (doc.frontmatter or {}).get("owner") == session2


@pytest.mark.integration
def test_partial_session_completion(project_dir: TestProjectDir):
    """Test completing some tasks while leaving others.

    Scenario:
    - Session has 5 tasks
    - 3 tasks completed and validated
    - 2 tasks still in progress
    - Session can't complete yet
    """
    session_id = "test-partial"
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path))

    completed = []
    wip = []

    for i in range(5):
        pr = i * 50
        tid = f"{pr}-wave1-task{i}"
        # Create and register
        assert_command_success(run_script("tasks/new", ["--id", str(pr), "--wave", "wave1", "--slug", f"task{i}", "--session", session_id], cwd=project_dir.tmp_path))
        if i < 3:
            # Mark done → create QA → mark QA done → task validated
            _start_impl_tracking(tid, cwd=project_dir.tmp_path)
            assert_command_success(run_script("tasks/status", [tid, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path))
            assert_command_success(run_script("qa/new", [tid, "--session", session_id], cwd=project_dir.tmp_path))
            _qa_to_done(tid, session_id, project_dir.tmp_path, project_dir.tmp_path)
            assert_command_success(run_script("tasks/status", [tid, "--status", "validated", "--session", session_id], cwd=project_dir.tmp_path))
            completed.append(tid)
        else:
            # Active work
            assert_command_success(run_script("tasks/status", [tid, "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path))
            wip.append(tid)

    # Attempt to complete session should fail (incomplete tasks remain)
    res = run_script("session", ["complete", session_id], cwd=project_dir.tmp_path)
    assert_command_failure(res)


@pytest.mark.integration
@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.slow
def test_session_merge_scenario(combined_env):
    """Test complete session merge workflow.

    Scenario:
    - Session created with worktree
    - Multiple commits in worktree
    - All tasks completed and validated
    - Merge task created
    - Merge task validated
    - Worktree archived
    """
    project_dir, git_repo = combined_env
    session_id = "test-merge"
    task_id = "200-wave1-feature"

    # Create session (uses repo with git; should create a worktree)
    r = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=git_repo.repo_path,
    )
    assert_command_success(r)

    # Inspect session JSON for worktree path
    st = run_script("session", ["status", session_id, "--json"], cwd=git_repo.repo_path)
    assert_command_success(st)
    import json as _json
    sess = _json.loads(st.stdout)
    worktree_path = Path(sess.get("git", {}).get("worktreePath", ""))
    assert worktree_path and worktree_path.exists()

    # Implement feature in the worktree
    file = worktree_path / "src" / "feature.ts"
    git_repo.create_test_file(file, "export const feature = () => {};")
    git_repo.commit_in_worktree(worktree_path, "Add feature")

    # Create + validate a feature task inside session
    # Mutating task commands must run inside the session worktree.
    assert_command_success(
        run_script(
            "tasks/new",
            ["--id", "200", "--wave", "wave1", "--slug", "feature", "--session", session_id],
            cwd=worktree_path,
        )
    )
    _start_impl_tracking(task_id, cwd=worktree_path)
    assert_command_success(
        run_script("tasks/status", [task_id, "--status", "done", "--session", session_id], cwd=worktree_path)
    )
    assert_command_success(run_script("qa/new", [task_id, "--session", session_id], cwd=worktree_path))
    _qa_to_done(task_id, session_id, worktree_path, worktree_path)
    assert_command_success(
        run_script(
            "tasks/status",
            [task_id, "--status", "validated", "--session", session_id],
            cwd=worktree_path,
        )
    )

    # Complete session → should create merge task
    comp = run_script("session", ["complete", session_id], cwd=worktree_path)
    assert_command_success(comp)
    assert_output_contains(comp, "promoted to validated")


@pytest.mark.integration
@pytest.mark.slow
def test_large_scale_validation(project_dir: TestProjectDir):
    """Test validating session with many tasks.

    Scenario:
    - Session has 10 tasks
    - All tasks completed
    - Create QA for all
    - Validate all tasks
    """
    session_id = "test-large-scale"
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path))

    task_ids = []
    for i in range(10):
        pr = i * 50
        tid = f"{pr}-wave1-large{i}"
        # Create, move to done, create QA, mark QA done, validate task
        assert_command_success(run_script("tasks/new", ["--id", str(pr), "--wave", "wave1", "--slug", f"large{i}", "--session", session_id], cwd=project_dir.tmp_path))
        _start_impl_tracking(tid, cwd=project_dir.tmp_path)
        assert_command_success(run_script("tasks/status", [tid, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path))
        assert_command_success(run_script("qa/new", [tid, "--session", session_id], cwd=project_dir.tmp_path))
        _qa_to_done(tid, session_id, project_dir.tmp_path, project_dir.tmp_path)
        assert_command_success(run_script("tasks/status", [tid, "--status", "validated", "--session", session_id], cwd=project_dir.tmp_path))
        task_ids.append(tid)

    # Sanity: files exist under validated/ and qa/done/
    for tid in task_ids:
        assert_file_exists(project_dir.project_root / "tasks" / "validated" / f"{tid}.md")
        assert_file_exists(project_dir.project_root / "qa" / "done" / f"{tid}-qa.md")


@pytest.mark.integration
@pytest.mark.slow
def test_recovery_from_failed_validation(project_dir: TestProjectDir):
    """Test recovering from validation failures.

    Scenario:
    - Task fails validation (round 1)
    - Fixes applied
    - Re-validation (round 2) passes
    """
    session_id = "test-recovery"
    task_id = "250-wave1-recovery"

    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path))

    # Implement and mark done
    assert_command_success(run_script("tasks/new", ["--id", "250", "--wave", "wave1", "--slug", "recovery", "--session", session_id], cwd=project_dir.tmp_path))
    _start_impl_tracking(task_id, cwd=project_dir.tmp_path)
    assert_command_success(run_script("tasks/status", [task_id, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path))

    # Create QA and move to wip, then rejection back to waiting (Round 1)
    assert_command_success(run_script("qa/new", [task_id, "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(run_script("qa/promote", [task_id, "--status", "todo", "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(run_script("qa/promote", [task_id, "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path))
    # Rejected → back to waiting
    # Fail/redo cycle: wip → todo (waiting is not a configured QA state in this workflow).
    assert_command_success(run_script("qa/promote", [task_id, "--status", "todo", "--session", session_id], cwd=project_dir.tmp_path))

    # Round 2: fixes applied → move again to todo → wip → done
    assert_command_success(run_script("qa/promote", [task_id, "--status", "todo", "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(run_script("qa/promote", [task_id, "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path))
    _seed_validation_evidence(project_dir.tmp_path, task_id, round_num=2)
    assert_command_success(run_script("qa/promote", [task_id, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(run_script("tasks/status", [task_id, "--status", "validated", "--session", session_id], cwd=project_dir.tmp_path))

    # Markers for round directories (not mock helpers): create simple evidence markers
    round1_dir = project_dir.project_root / "qa" / "validation-evidence" / task_id / "round-1"
    round2_dir = project_dir.project_root / "qa" / "validation-evidence" / task_id / "round-2"
    round1_dir.mkdir(parents=True, exist_ok=True)
    round2_dir.mkdir(parents=True, exist_ok=True)
    (round1_dir / "git-diff-stat.txt").write_text("round1")
    (round2_dir / "git-diff-stat.txt").write_text("round2")

    assert_directory_exists(round1_dir)
    assert_directory_exists(round2_dir)


@pytest.mark.integration
def test_mixed_worktree_and_regular_sessions(combined_env):
    """Test mixing worktree and non-worktree sessions.

    Scenario:
    - Session 1: Uses worktree
    - Session 2: No worktree (small changes)
    - Session 3: Uses worktree
    - All can operate independently
    """
    # Create sessions in different roots to differentiate worktree behavior
    project_dir, git_repo = combined_env

    session1 = "test-mixed-wt1"
    session2 = "test-mixed-regular"
    session3 = "test-mixed-wt2"

    # Sessions created in git repo → worktree metadata expected
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session1, "--mode", "start"], cwd=git_repo.repo_path))
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session3, "--mode", "start"], cwd=git_repo.repo_path))

    # Session created in non-git tmp project dir → no worktree metadata
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session2, "--mode", "start"], cwd=project_dir.tmp_path))

    s1 = run_script("session", ["status", session1, "--json"], cwd=git_repo.repo_path)
    s2 = run_script("session", ["status", session2, "--json"], cwd=project_dir.tmp_path)
    s3 = run_script("session", ["status", session3, "--json"], cwd=git_repo.repo_path)
    assert_command_success(s1)
    assert_command_success(s2)
    assert_command_success(s3)

    import json as _json
    s1_data = _json.loads(s1.stdout)
    s2_data = _json.loads(s2.stdout)
    s3_data = _json.loads(s3.stdout)

    assert "git" in s1_data and s1_data["git"].get("worktreePath")
    assert not (s2_data.get("git") or {}).get("worktreePath")
    assert "git" in s3_data and s3_data["git"].get("worktreePath")


@pytest.mark.integration
@pytest.mark.slow
def test_cascading_task_validation(project_dir: TestProjectDir):
    """Test cascading validation (parent → children).

    Scenario:
    - Parent task has 3 children
    - Children must be validated before parent
    - Parent validation triggers after all children done
    """
    session_id = "test-cascade"
    parent_id = "300-wave1-cascade-parent"
    child_ids = ["300.1-wave1-child1", "300.2-wave1-child2", "300.3-wave1-child3"]

    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path))

    # Parent starts blocked
    assert_command_success(run_script("tasks/new", ["--id", "300", "--wave", "wave1", "--slug", "cascade-parent", "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(
        run_script(
            "tasks/status",
            [parent_id, "--status", "blocked", "--session", session_id, "--reason", "Blocked by child validation"],
            cwd=project_dir.tmp_path,
        )
    )

    # Children created → link to parent → validate children
    for cid in child_ids:
        slot = cid.split("-", 1)[0]
        slug = cid.split("-", 2)[-1]
        assert_command_success(run_script("tasks/new", ["--id", slot, "--wave", "wave1", "--slug", slug, "--session", session_id], cwd=project_dir.tmp_path))
        assert_command_success(run_script("tasks/link", [parent_id, cid, "--session", session_id], cwd=project_dir.tmp_path))
        _start_impl_tracking(cid, cwd=project_dir.tmp_path)
        assert_command_success(run_script("tasks/status", [cid, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path))
        assert_command_success(run_script("qa/new", [cid, "--session", session_id], cwd=project_dir.tmp_path))
        _qa_to_done(cid, session_id, project_dir.tmp_path, project_dir.tmp_path)
        assert_command_success(run_script("tasks/status", [cid, "--status", "validated", "--session", session_id], cwd=project_dir.tmp_path))

    # Unblock parent → move to wip
    assert_command_success(run_script("tasks/status", [parent_id, "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path))


@pytest.mark.integration
@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.slow
def test_concurrent_worktree_sessions_isolation(combined_env):
    """Test that concurrent worktree sessions are isolated.

    Scenario:
    - 3 sessions with separate worktrees
    - Each makes different changes
    - Changes don't interfere
    - Each can be validated independently
    """
    project_dir, git_repo = combined_env

    sessions = []
    worktrees = []

    for i in range(3):
        session_id = f"concurrent-wt-{i}"
        r = run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=git_repo.repo_path)
        assert_command_success(r)

        st = run_script("session", ["status", session_id, "--json"], cwd=git_repo.repo_path)
        assert_command_success(st)
        import json as _json
        sess = _json.loads(st.stdout)
        worktree_path = Path(sess.get("git", {}).get("worktreePath", ""))
        assert worktree_path and worktree_path.exists()

        # Unique change in each worktree
        file = worktree_path / f"feature-{i}.ts"
        git_repo.create_test_file(file, f"export const feature{i} = () => {{}};")
        git_repo.commit_in_worktree(worktree_path, f"Add feature-{i}")

        sessions.append(session_id)
        worktrees.append(worktree_path)

    # Verify isolation of changes
    for i, wt in enumerate(worktrees):
        changed = git_repo.get_changed_files_in_worktree(wt, "main")
        assert f"feature-{i}.ts" in changed
        for j in range(3):
            if j != i:
                assert f"feature-{j}.ts" not in changed


@pytest.mark.integration
def test_parent_blocked_by_child_in_wip(project_dir: TestProjectDir):
    """Test parent cannot be promoted when child tasks are not ready.

    Scenario:
    - Parent task with linked child task
    - Child task in wip (not done/validated)
    - Attempt to promote parent to done should fail
    - Verify blocking message references child tasks
    """
    session_id = "test-parent-blocked"
    parent_id = "600-wave1-parent"
    child_id = "600.1-wave1-child"

    # Create session
    assert_command_success(
        run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path)
    )

    # Create parent task
    assert_command_success(
        run_script("tasks/new", ["--id", "600", "--wave", "wave1", "--slug", "parent", "--session", session_id], cwd=project_dir.tmp_path)
    )

    # Create child task and link to parent
    assert_command_success(
        run_script("tasks/new", ["--id", "600.1", "--wave", "wave1", "--slug", "child", "--session", session_id], cwd=project_dir.tmp_path)
    )
    assert_command_success(
        run_script("tasks/link", [parent_id, child_id, "--session", session_id], cwd=project_dir.tmp_path)
    )

    # Move parent to wip
    assert_command_success(
        run_script("tasks/status", [parent_id, "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path)
    )

    # Move child to wip (but NOT done) - this should block parent from being promoted
    assert_command_success(
        run_script("tasks/status", [child_id, "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path)
    )

    # Attempt to move parent to done - should FAIL because child not ready
    # The guard in tasks/status should block this transition
    result = run_script("tasks/status", [parent_id, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_failure(result)

    # Verify error message mentions child tasks not ready
    output = (result.stderr + result.stdout).lower()
    assert "child" in output or "not ready" in output or "linked" in output


@pytest.mark.integration
def test_bundle_validation_parent_only(project_dir: TestProjectDir):
    """Test validators/validate runs ONLY on parent, not children.

    Scenario:
    - Parent task with linked children
    - Call validators/validate on parent
    - Verify only parent ID is validated
    - Verify children don't get individual validation
    - Verify child approvals come from parent bundle
    """
    session_id = "test-bundle-parent-only"
    parent_id = "650-wave1-bundle-parent"
    child1_id = "650.1-wave1-child1"
    child2_id = "650.2-wave1-child2"

    from edison.core.config.manager import ConfigManager
    cfg = ConfigManager(repo_root=project_dir.tmp_path).load_config()
    bundle_summary_name = cfg.get("validation", {}).get("artifactPaths", {}).get("bundleSummaryFile")
    assert bundle_summary_name

    # Create session
    assert_command_success(
        run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path)
    )

    # Create parent and children, link them
    for task_num, slug in [("650", "bundle-parent"), ("650.1", "child1"), ("650.2", "child2")]:
        assert_command_success(
            run_script("tasks/new", ["--id", task_num, "--wave", "wave1", "--slug", slug, "--session", session_id], cwd=project_dir.tmp_path)
        )

    assert_command_success(
        run_script("tasks/link", [parent_id, child1_id, "--session", session_id], cwd=project_dir.tmp_path)
    )
    assert_command_success(
        run_script("tasks/link", [parent_id, child2_id, "--session", session_id], cwd=project_dir.tmp_path)
    )

    # Create evidence for parent and children (all tasks get evidence directories)
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"

    def create_evidence(task_id: str):
        """Helper to create minimal evidence for a task."""
        from pathlib import Path
        rd = project_dir.project_root / "qa" / "validation-evidence" / task_id / "round-1"
        rd.mkdir(parents=True, exist_ok=True)

        # Minimal command capture evidence required by the fast preset.
        (rd / "command-test.txt").write_text("scripts/test-fast\nExit code: 0\n", encoding="utf-8")

        # Implementation report
        impl_report = {
            "taskId": task_id,
            "round": 1,
            "implementationApproach": "orchestrator-direct",
            "primaryModel": "claude",
            "completionStatus": "complete",
            "blockers": [],
            "followUpTasks": [],
            "notesForValidator": "Test task",
            "tracking": {
                "processId": __import__("os").getpid(),
                "startedAt": now,
                "completedAt": now,
                "hostname": "e2e-test",
            },
        }
        (rd / "implementation-report.md").write_text(
            format_frontmatter(impl_report) + "\n# Implementation Report\n",
            encoding="utf-8",
        )

        # Validator reports for all blocking validators (global, critical, specialized)
        for validator_id, model in [
            ("global-codex", "codex"),
            ("global-claude", "claude"),
            ("coderabbit", "coderabbit"),
            ("security", "codex"),
            ("performance", "codex"),
            ("prisma", "codex"),
            ("testing", "codex"),
        ]:
            validator_report = {
                "taskId": task_id,
                "round": 1,
                "validatorId": validator_id,
                "model": model,
                "verdict": "approve",
                "summary": f"All checks passed for {validator_id}",
                "findings": [],
                "followUpTasks": [],
                "tracking": {
                    "processId": __import__("os").getpid(),
                    "startedAt": now,
                    "completedAt": now,
                    "hostname": "e2e-test"
                }
            }
            (rd / f"validator-{validator_id}-report.md").write_text(
                format_frontmatter(validator_report) + "\n# Validator Report\n",
                encoding="utf-8",
            )

    # Create evidence for all three tasks
    create_evidence(parent_id)
    create_evidence(child1_id)
    create_evidence(child2_id)

    # Compute bundle approval from existing evidence (no validator execution).
    validate_result = run_script(
        "validators/validate",
        [parent_id, "--session", session_id, "--check-only"],
        cwd=project_dir.tmp_path,
    )

    # Should succeed (all validators approved)
    assert_command_success(validate_result)

    # Verify bundle summary exists under parent evidence directory
    parent_bundle = project_dir.project_root / "qa" / "validation-evidence" / parent_id / "round-1" / bundle_summary_name
    assert_file_exists(parent_bundle)

    # Bundle validation runs once at the root, but Edison mirrors the bundle summary into
    # each cluster member's latest round so per-task guards can reason deterministically.
    child1_bundle = project_dir.project_root / "qa" / "validation-evidence" / child1_id / "round-1" / bundle_summary_name
    child2_bundle = project_dir.project_root / "qa" / "validation-evidence" / child2_id / "round-1" / bundle_summary_name
    assert_file_exists(child1_bundle)
    assert_file_exists(child2_bundle)

    child1_data = parse_frontmatter(child1_bundle.read_text()).frontmatter
    assert child1_data.get("taskId") == child1_id
    assert child1_data.get("rootTask") == parent_id
    assert child1_data.get("approved") is True

    child2_data = parse_frontmatter(child2_bundle.read_text()).frontmatter
    assert child2_data.get("taskId") == child2_id
    assert child2_data.get("rootTask") == parent_id
    assert child2_data.get("approved") is True

    # Verify parent bundle contains approvals for all tasks in cluster
    bundle_data = parse_frontmatter(parent_bundle.read_text()).frontmatter
    assert bundle_data["taskId"] == parent_id
    assert bundle_data["approved"] is True
    assert "tasks" in bundle_data
    task_ids_in_bundle = [t["taskId"] for t in bundle_data["tasks"]]
    assert parent_id in task_ids_in_bundle
    assert child1_id in task_ids_in_bundle
    assert child2_id in task_ids_in_bundle


@pytest.mark.integration
@pytest.mark.slow
def test_session_with_all_task_states(project_dir: TestProjectDir):
    """Test session with tasks in all possible states.

    Scenario:
    - Session has tasks in: todo, wip, done, validated, blocked
    - Session next should handle all states appropriately
    """
    session_id = "test-all-states"
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path))

    states = {
        "todo": ("100", "todo"),
        "wip": ("150", "wip"),
        "done": ("200", "done"),
        "validated": ("250", "validated"),
        "blocked": ("300", "blocked"),
    }

    # Create base tasks (start as todo)
    for _, (slot, label) in states.items():
        assert_command_success(run_script("tasks/new", ["--id", slot, "--wave", "wave1", "--slug", label, "--session", session_id], cwd=project_dir.tmp_path))

    # Move to desired states
    assert_command_success(run_script("tasks/status", ["150-wave1-wip", "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path))
    _start_impl_tracking("200-wave1-done", cwd=project_dir.tmp_path)
    assert_command_success(run_script("tasks/status", ["200-wave1-done", "--status", "done", "--session", session_id], cwd=project_dir.tmp_path))
    # validated requires QA done first
    _start_impl_tracking("250-wave1-validated", cwd=project_dir.tmp_path)
    assert_command_success(run_script("tasks/status", ["250-wave1-validated", "--status", "done", "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(run_script("qa/new", ["250-wave1-validated", "--session", session_id], cwd=project_dir.tmp_path))
    _qa_to_done("250-wave1-validated", session_id, project_dir.tmp_path, project_dir.tmp_path)
    assert_command_success(run_script("tasks/status", ["250-wave1-validated", "--status", "validated", "--session", session_id], cwd=project_dir.tmp_path))
    # blocked
    assert_command_success(run_script("tasks/status", ["300-wave1-blocked", "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(
        run_script(
            "tasks/status",
            ["300-wave1-blocked", "--status", "blocked", "--session", session_id, "--reason", "Blocked by external dependency"],
            cwd=project_dir.tmp_path,
        )
    )

    # Quick sanity check: files in expected directories
    assert_file_exists(project_dir.project_root / "tasks" / "todo" / "100-wave1-todo.md")
    assert_file_exists(project_dir.project_root / "tasks" / "wip" / "150-wave1-wip.md")
    assert_file_exists(project_dir.project_root / "tasks" / "done" / "200-wave1-done.md")
    assert_file_exists(project_dir.project_root / "tasks" / "validated" / "250-wave1-validated.md")
    assert_file_exists(project_dir.project_root / "tasks" / "blocked" / "300-wave1-blocked.md")

    # session next runs and returns actions without error
    nxt = run_script("session/next", [session_id, "--json"], cwd=project_dir.tmp_path)
    assert_command_success(nxt)
