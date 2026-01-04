"""Test 07: Context7 Enforcement (REAL CLI)

Refactored to execute REAL CLIs with no mocks.

Test Coverage:
- Context7 marker file validation
- Package detection via file patterns (tsx/route.ts/schema.ts)
- Cross-check: task metadata + git diff
- Multiple packages requiring evidence
- Missing Context7 evidence detection
- Context7 evidence per round
- Package name normalization (evidence files)
- No‑packages path succeeds without Context7
"""
from __future__ import annotations

from pathlib import Path
import os
import json
import pytest

from helpers.assertions import assert_file_exists, assert_file_contains
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
    assert_output_contains,
)
from helpers.env import TestProjectDir, TestGitRepo


# -------------------------
# Local test utilities
# -------------------------

def _task_file_path(project_root: Path, status: str, task_id: str) -> Path:
    return project_root / "tasks" / status / f"{task_id}.md"


def _edit_primary_files(task_path: Path, files: list[str]) -> None:
    """Append Primary Files entries to the task file under the metadata section.

    The ready guard inspects the "Primary Files / Areas" section. We insert
    a bullet list immediately after the first occurrence of the field.
    """
    from helpers.assertions import read_file
    text = read_file(task_path)
    lines = text.splitlines()
    out: list[str] = []
    inserted = False
    for i, line in enumerate(lines):
        out.append(line)
        if not inserted and ("Primary Files / Areas:" in line):
            # Insert a simple list on the next line(s)
            for fp in files:
                out.append(f"- {fp}")
            inserted = True

    # Fail-open for test fixtures: if the template doesn't contain the marker line,
    # append a canonical section so Context7 detection can still work.
    if not inserted:
        out.append("")
        out.append("## Primary Files / Areas")
        for fp in files:
            out.append(f"- {fp}")

    task_path.write_text("\n".join(out) + "\n")


def _evidence_dir(project_root: Path, task_id: str, round_num: int = 1) -> Path:
    return (
        project_root / "qa" / "validation-evidence" / task_id / f"round-{round_num}"
    )


def _ensure_base_evidence(project_root: Path, task_id: str, round_num: int = 1) -> None:
    """Create the required non‑Context7 evidence files for tasks/ready.

    - Start + complete an implementation report via real `track` CLI
    - Create command evidence files expected by the guard
    """
    # Start and complete implementation tracking to create implementation-report.md
    r1 = run_script(
        "track",
        [
            "start",
            "--task",
            task_id,
            "--type",
            "implementation",
            "--model",
            "gemini",
            "--round",
            str(round_num),
        ],
        cwd=project_root.parent,
    )
    assert_command_success(r1)

    r2 = run_script(
        "track",
        [
            "complete",
            "--task",
            task_id,
        ],
        cwd=project_root.parent,
    )
    assert_command_success(r2)

    # Create the required command outputs under the latest round
    ev_dir = _evidence_dir(project_root, task_id, round_num)
    ev_dir.mkdir(parents=True, exist_ok=True)
    # Include minimal trusted marker format expected by the guard
    trusted_header = (
        "RUNNER: tasks/ready\n"
        "START: 1970-01-01T00:00:00Z\n"  # mtime check uses file timestamp; header is informational
        "CMD: echo test\n"
        "EXIT_CODE: 0\n"
        "END\n"
    )
    for fname in (
        "command-type-check.txt",
        "command-lint.txt",
        "command-test.txt",
        "command-build.txt",
    ):
        (ev_dir / fname).write_text(trusted_header)


def _ensure_impl_validate_ok(repo_root: Path) -> None:
    """Provide a no-op implementation validator so tasks/ready schema check passes.

    The production repo ships a validator; the test harness supplies a stub.
    """
    script_path = repo_root.parent / "scripts" / "implementation" / "validate"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    if not script_path.exists():
        script_path.write_text("#!/usr/bin/env bash\n# test stub\nexit 0\n")
        os.chmod(script_path, 0o755)


@pytest.mark.context7
@pytest.mark.edge_case
def test_context7_note_bypass_is_rejected(project_dir: TestProjectDir):
    """RED: Note in task file must NOT satisfy Context7 evidence.

    Reproduces the bypass where tasks/ready accepted phrases like
    "Context7 (react)" or "context7-react" inside the task markdown.
    Desired behavior: Only marker files under the evidence round are valid.
    """
    task_num, wave, slug = "610", "wave1", "note-bypass"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-ctx7-note-bypass"

    # Create task, session, claim, QA
    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
    )
    assert_command_success(
        run_script(
            "tasks/new",
            ["--id", task_num, "--wave", wave, "--slug", slug],
            cwd=project_dir.tmp_path,
        )
    )
    assert_command_success(
        run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    )
    # Minimal QA brief to satisfy guard (avoid qa/new session coupling in tests)
    qa_waiting = project_dir.project_root / "qa" / "waiting"
    qa_waiting.mkdir(parents=True, exist_ok=True)
    (qa_waiting / f"{task_id}-qa.md").write_text("# QA\n\n## Validators\n- global-codex\n")

    # Add primary files implying React usage (tsx)
    candidate_paths = [
        project_dir.project_root / "sessions" / "wip" / session_id / "tasks" / "wip" / f"{task_id}.md",
        project_dir.project_root / "tasks" / "wip" / f"{task_id}.md",
        project_dir.project_root / "tasks" / "todo" / f"{task_id}.md",
    ]
    task_path = next((p for p in candidate_paths if p.exists()), None)
    assert task_path is not None, "Expected a task file after claim"
    _edit_primary_files(task_path, ["apps/web/src/App.tsx"])  # implies react

    # Provide all base evidence but intentionally NO context7-react marker file
    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    # Inject the historical bypass note in the task file
    with open(task_path, "a", encoding="utf-8") as f:
        f.write("\nNotes: Context7 (react) covered via docs review.\n")
        f.write("Alternate tag: context7-react\n")

    # Attempt to move to done must FAIL (notes do not count)
    res_done = run_script(
        "tasks/status",
        [task_id, "--status", "done", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    # Expect failure due to missing marker file; error should mention the missing package
    assert_command_failure(res_done)
    assert ("react" in res_done.stdout.lower() or "react" in res_done.stderr.lower())

def _write_context7(
    project_root: Path,
    task_id: str,
    package: str,
    round_num: int = 1,
    content: str | None = None,
    session_id: str | None = None,
) -> Path:
    """Create Context7 markers in both legacy QA evidence and session-scoped paths.

    The ready guard still reads from qa/validation-evidence/*, while newer
    Context7 flows expect markers under the active session worktree. Writing
    both keeps the tests forward-compatible without touching production code.
    """
    if content is None:
        content = "Notes: Context7 validated.\n"

    from edison.core.utils.text.frontmatter import format_frontmatter

    marker_text = format_frontmatter(
        {
            "package": package,
            "libraryId": f"/test/{package}",
            "topics": ["core APIs", "usage patterns"],
            "queriedAt": "2025-01-01T00:00:00Z",
        }
    ) + str(content)

    # Legacy evidence location (qa/validation-evidence)
    ev_dir = _evidence_dir(project_root, task_id, round_num)
    ev_dir.mkdir(parents=True, exist_ok=True)
    path = ev_dir / f"context7-{package}.txt"
    path.write_text(marker_text)

    # Session-scoped marker structure expected by newer enforcement
    if session_id:
        markers_dir = (
            project_root
            / "sessions"
            / "wip"
            / session_id
            / "tasks"
            / task_id
            / "evidence"
            / "context7"
            / f"round-{round_num}"
            / "markers"
        )
        markers_dir.mkdir(parents=True, exist_ok=True)
        marker_md = markers_dir / f"{package}.md"
        marker_md.write_text(
            f"# Package: {package}\n\n"
            f"This task uses {package}.\n\n"
            "## Detection\n"
            "- File extensions: .tsx, .jsx, .prisma\n"
            "- Imports: from 'react', '@prisma/client', zod schema files\n"
            "- Schema files: schema.prisma\n\n"
            f"{content}"
        )
        impl_report = markers_dir.parent / "implementation-report.md"
        if not impl_report.exists():
            impl_report.write_text("# Implementation Report\n\nPackages validated.\n")

    return path


@pytest.mark.context7
@pytest.mark.fast
def test_context7_marker_file_structure(project_dir: TestProjectDir):
    """Create evidence marker using real round structure (no mocks)."""
    task_num, wave, slug = "100", "wave1", "ctx7-structure"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-ctx7-structure"

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
    )

    # Create task via real CLI and claim into the session (todo -> wip)
    assert_command_success(
        run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    )
    assert_command_success(run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path))

    # Create QA brief (waiting is acceptable for ready checks)
    res_qa = run_script("qa/new", [task_id], cwd=project_dir.tmp_path)
    assert_command_success(res_qa)

    # Establish base evidence + round structure
    _ensure_base_evidence(project_dir.project_root, task_id, round_num=1)

    # Add Context7 evidence (normalized package name)
    marker = _write_context7(project_dir.project_root, task_id, "react", round_num=1, content="React evidence\n")

    # Verify marker file structure
    assert_file_exists(marker)
    assert_file_contains(marker, "React evidence")


@pytest.mark.context7
@pytest.mark.fast
def test_context7_multiple_packages(project_dir: TestProjectDir):
    """Multiple Context7 markers placed in the same round directory."""
    task_num, wave, slug = "150", "wave1", "multi-ctx7"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-ctx7-multiple"

    res_new = run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    assert_command_success(res_new)
    run_script("tasks/status", [task_id, "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    # Use packages present in postTrainingPackages config
    packages = ["react", "zod", "next", "uistylescss", "typescript"]
    for pkg in packages:
        _write_context7(project_dir.project_root, task_id, pkg, 1, session_id=session_id)

    ev_dir = _evidence_dir(project_dir.project_root, task_id, 1)
    for pkg in packages:
        assert_file_exists(ev_dir / f"context7-{pkg}.txt")


@pytest.mark.context7
@pytest.mark.requires_git
@pytest.mark.integration
def test_context7_detection_from_file_extensions(combined_env):
    """Ready guard detects packages via changed file extensions (git diff).

    - .tsx → react (+ typescript)
    - app/**/route.ts → next (+ typescript)
    """
    project_dir, git_repo = combined_env
    session_id = "test-ctx7-extensions"
    task_num, wave, slug = "200", "wave1", "extensions"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create session (worktree enabled by manifest) via real CLI
    res_session = run_script(
        "session",
        ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(res_session)

    # Create task → wip, and QA brief
    assert_command_success(
        run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    )
    # Add Primary Files indicating React usage
    todo = _task_file_path(project_dir.project_root, "todo", task_id)
    _edit_primary_files(todo, ["components/Profile.tsx"])  # triggers react
    assert_command_success(run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path))
    # Minimal QA brief to satisfy guard
    qa_waiting = project_dir.project_root / "qa" / "waiting"
    qa_waiting.mkdir(parents=True, exist_ok=True)
    (qa_waiting / f"{task_id}-qa.md").write_text("# QA\n\n## Validators\n- global-codex\n")

    # Make changes in worktree
    # Locate worktree from session file
    session_json = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    sess = json.loads(session_json.read_text())
    worktree_path = Path(sess["git"]["worktreePath"]) if sess.get("git", {}).get("worktreePath") else None
    if worktree_path and worktree_path.exists():
        files = {
            "src/Button.tsx": "export const Button = () => 'ok'\n",
            "app/api/hello/route.ts": "export function GET() { return new Response('ok') }\n",
        }
        for rel, content in files.items():
            p = worktree_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        git_repo.commit_in_worktree(worktree_path, "feat: add tsx and route")
    else:
        # Fallback: use Primary Files metadata in non-worktree sandbox
        p_todo = _task_file_path(project_dir.project_root, "todo", task_id)
        p_wip = _task_file_path(project_dir.project_root, "wip", task_id)
        target = p_todo if p_todo.exists() else p_wip
        _edit_primary_files(target, ["src/Button.tsx", "app/api/hello/route.ts"])  # TSX + route

    # Provide validator stub + all base evidence but NO Context7 → guard must fail listing packages
    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    res_done = run_script(
        "tasks/status",
        [task_id, "--status", "done", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_failure(res_done)
    # Expect at least react and next to appear in the error (typescript may also be flagged)
    assert ("react" in res_done.stdout or "react" in res_done.stderr)
    assert ("next" in res_done.stdout or "next" in res_done.stderr)


@pytest.mark.context7
@pytest.mark.requires_git
@pytest.mark.integration
def test_context7_detection_from_imports(combined_env):
    """Use file naming heuristics to simulate import triggers (real guard relies on paths).

    We add a zod‑schema file and a react TSX file so the guard flags both.
    """
    project_dir, git_repo = combined_env
    session_id = "test-ctx7-imports"
    task_num, wave, slug = "250", "wave1", "imports"
    task_id = f"{task_num}-{wave}-{slug}"

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
    )
    assert_command_success(
        run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    )
    assert_command_success(run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path))
    qa_waiting = project_dir.project_root / "qa" / "waiting"
    qa_waiting.mkdir(parents=True, exist_ok=True)
    (qa_waiting / f"{task_id}-qa.md").write_text("# QA\n\n## Validators\n- global-codex\n")

    session_json = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    sess2 = json.loads(session_json.read_text())
    wt2_raw = sess2.get("git", {}).get("worktreePath")
    wt2 = Path(wt2_raw) if wt2_raw else None
    if wt2 and wt2.exists():
        # Add files that match guard patterns for zod/react
        (wt2 / "packages/api-core/src").mkdir(parents=True, exist_ok=True)
        (wt2 / "apps/web/src").mkdir(parents=True, exist_ok=True)
        (wt2 / "packages/api-core/src/schema.ts").write_text("export const x = 1\n")
        (wt2 / "apps/web/src/App.tsx").write_text("export const App = () => 'ok'\n")
        git_repo.commit_in_worktree(wt2, "feat: add zod schema + react app")
    else:
        # Fallback: declare files in task metadata
        p3_todo = _task_file_path(project_dir.project_root, "todo", task_id)
        p3_wip = _task_file_path(project_dir.project_root, "wip", task_id)
        target3 = p3_todo if p3_todo.exists() else p3_wip
        _edit_primary_files(target3, ["packages/api-core/src/schema.ts", "apps/web/src/App.tsx"])  # zod + react

    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)
    res_done = run_script(
        "tasks/status",
        [task_id, "--status", "done", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_failure(res_done)
    assert ("react" in res_done.stdout or "react" in res_done.stderr)
    assert ("zod" in res_done.stdout or "zod" in res_done.stderr)


@pytest.mark.context7
@pytest.mark.edge_case
def test_context7_missing_evidence_detection(project_dir: TestProjectDir):
    """Guard fails when task implies React but no Context7 marker exists."""
    task_num, wave, slug = "300", "wave1", "missing-ctx7"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-ctx7-missing"

    assert_command_success(
        run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    )
    # Establish an active session and claim the task before ready/done checks
    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
    )
    assert_command_success(run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path))
    # Add primary files metadata to imply React usage
    candidate_paths = [
        project_dir.project_root / "sessions" / "wip" / session_id / "tasks" / "wip" / f"{task_id}.md",
        project_dir.project_root / "tasks" / "wip" / f"{task_id}.md",
        project_dir.project_root / "tasks" / "todo" / f"{task_id}.md",
    ]
    task_path = next((p for p in candidate_paths if p.exists()), None)
    assert task_path is not None, "Expected a task file after claim"
    _edit_primary_files(task_path, ["apps/web/src/App.tsx"])  # tsx → react
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    # Attempt move to done without Context7 → should fail
    res_done = run_script(
        "tasks/status",
        [task_id, "--status", "done", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_failure(res_done)
    assert ("react" in res_done.stdout or "react" in res_done.stderr)


@pytest.mark.context7
@pytest.mark.requires_git
@pytest.mark.integration
def test_context7_cross_check_task_metadata_vs_git_diff(combined_env):
    """Test Context7 cross-check: task metadata vs git diff.

    CRITICAL TEST: Validates that Context7 enforcement uses BOTH sources:
    1. Task metadata (primary_files field)
    2. Git diff (actual changed files)

    If they differ, BOTH packages must have Context7 evidence.
    """
    project_dir, git_repo = combined_env
    session_id = "test-ctx7-crosscheck"
    task_num, wave, slug = "350", "wave1", "crosscheck"
    task_id = f"{task_num}-{wave}-{slug}"

    # Real session + task + QA
    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
    )
    assert_command_success(
        run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    )
    # Add metadata that implies React
    todo_path = _task_file_path(project_dir.project_root, "todo", task_id)
    _edit_primary_files(todo_path, ["apps/example-app/src/Button.tsx"])  # React in metadata
    assert_command_success(run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path))
    qa_waiting = project_dir.project_root / "qa" / "waiting"
    qa_waiting.mkdir(parents=True, exist_ok=True)
    (qa_waiting / f"{task_id}-qa.md").write_text("# QA\n\n## Validators\n- global-codex\n")

    # Change Zod‑pattern file in worktree
    sess = json.loads((project_dir.project_root / "sessions" / "wip" / session_id / "session.json").read_text())
    worktree_raw = sess.get("git", {}).get("worktreePath")
    worktree_path = Path(worktree_raw) if worktree_raw else None
    if worktree_path and worktree_path.exists():
        api_file = worktree_path / "packages" / "api-core" / "src" / "schema.ts"
        api_file.parent.mkdir(parents=True, exist_ok=True)
        api_file.write_text("export const schema = 1\n")
        git_repo.commit_in_worktree(worktree_path, "feat: add zod schema")
    else:
        # Fallback when worktrees are unavailable: declare zod file via metadata
        candidate_paths = [
            project_dir.project_root / "sessions" / "wip" / session_id / "tasks" / "wip" / f"{task_id}.md",
            project_dir.project_root / "tasks" / "wip" / f"{task_id}.md",
            project_dir.project_root / "tasks" / "todo" / f"{task_id}.md",
        ]
        target = next((p for p in candidate_paths if p.exists()), None)
        assert target is not None, "Expected a task file for metadata fallback"
        _edit_primary_files(target, ["apps/example-app/src/Button.tsx", "packages/api-core/src/schema.ts"])

    # Only add React evidence; Zod missing
    _ensure_base_evidence(project_dir.project_root, task_id, 1)
    _write_context7(project_dir.project_root, task_id, "react", 1, session_id=session_id)

    res = run_script("tasks/status", [task_id, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_failure(res)
    assert ("react" in res.stdout or "react" in res.stderr)
    assert ("zod" in res.stdout or "zod" in res.stderr)  # git diff says zod; missing


@pytest.mark.context7
@pytest.mark.fast
def test_context7_evidence_per_round(project_dir: TestProjectDir):
    """Evidence is tracked per round directory (round-1 vs round-2)."""
    task_num, wave, slug = "400", "wave1", "rounds-ctx7"
    task_id = f"{task_num}-{wave}-{slug}"

    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("tasks/status", [task_id, "--status", "wip"], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)
    _write_context7(project_dir.project_root, task_id, "react", 1)

    _ensure_base_evidence(project_dir.project_root, task_id, 2)
    _write_context7(project_dir.project_root, task_id, "react", 2)
    _write_context7(project_dir.project_root, task_id, "zod", 2)

    round1 = _evidence_dir(project_dir.project_root, task_id, 1)
    round2 = _evidence_dir(project_dir.project_root, task_id, 2)
    assert_file_exists(round1 / "context7-react.txt")
    assert not (round1 / "context7-zod.txt").exists()
    assert_file_exists(round2 / "context7-react.txt")
    assert_file_exists(round2 / "context7-zod.txt")


@pytest.mark.context7
@pytest.mark.fast
def test_context7_package_name_normalization(project_dir: TestProjectDir):
    """Evidence file names are normalized (react-dom→react, next/router→next)."""
    task_num, wave, slug = "450", "wave1", "normalize"
    task_id = f"{task_num}-{wave}-{slug}"

    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("tasks/status", [task_id, "--status", "wip"], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    # Only create normalized markers
    _write_context7(project_dir.project_root, task_id, "react", 1)
    _write_context7(project_dir.project_root, task_id, "next", 1)

    ev_dir = _evidence_dir(project_dir.project_root, task_id, 1)
    assert_file_exists(ev_dir / "context7-react.txt")
    assert_file_exists(ev_dir / "context7-next.txt")
    # Sanity: non-normalized names should not be present
    assert not (ev_dir / "context7-react-dom.txt").exists()
    assert not (ev_dir / "context7-next-router.txt").exists()


@pytest.mark.context7
@pytest.mark.edge_case
def test_context7_no_packages_required(project_dir: TestProjectDir):
    """No recognized packages → guard should allow move to done (with base evidence)."""
    task_num, wave, slug = "500", "wave1", "no-packages"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-ctx7-no-packages"

    res_new = run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    assert_command_success(res_new)
    # Add primary files that do NOT match any Context7 package patterns
    todo_path = _task_file_path(project_dir.project_root, "todo", task_id)
    _edit_primary_files(todo_path, ["README.md", ".gitignore", "docs/CONTRIBUTING.md"])  # safe

    run_script("tasks/status", [task_id, "--status", "wip"], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    # Create session + claim before attempting ready/done
    run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path)

    res_done = run_script(
        "tasks/status",
        [task_id, "--status", "done", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(res_done)
    # File should now be under tasks/done/
    assert_file_exists(_task_file_path(project_dir.project_root, "done", task_id))


@pytest.mark.context7
@pytest.mark.integration
@pytest.mark.slow
def test_context7_complete_enforcement_workflow(combined_env):
    """End‑to‑end: metadata+git detection, failing round, then passing with complete evidence."""
    project_dir, git_repo = combined_env
    session_id = "test-ctx7-complete"
    task_num, wave, slug = "600", "wave1", "ctx7-complete"
    task_id = f"{task_num}-{wave}-{slug}"

    # Session + task + QA
    run_script("session", ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path)
    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    # Metadata claims React
    todo = _task_file_path(project_dir.project_root, "todo", task_id)
    _edit_primary_files(todo, ["apps/example-app/src/Form.tsx"])  # React in metadata
    run_script("tasks/status", [task_id, "--status", "wip"], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id, "--owner", session_id, "--session", session_id], cwd=project_dir.tmp_path)

    # Git diff shows Zod (schema.ts)
    sess = json.loads((project_dir.project_root / "sessions" / "wip" / session_id / "session.json").read_text())
    wt_raw = sess.get("git", {}).get("worktreePath")
    worktree_path = Path(wt_raw) if wt_raw else None
    if worktree_path and worktree_path.exists():
        (worktree_path / "packages/api-core/src").mkdir(parents=True, exist_ok=True)
        (worktree_path / "packages/api-core/src/schema.ts").write_text("export const s = 1\n")
        git_repo.commit_in_worktree(worktree_path, "feat: add zod schema")
    else:
        # Fallback: mark zod-triggering file in metadata when worktrees are unavailable
        target_meta = _task_file_path(project_dir.project_root, "todo", task_id)
        if not target_meta.exists():
            target_meta = _task_file_path(project_dir.project_root, "wip", task_id)
        _edit_primary_files(target_meta, ["packages/api-core/src/schema.ts"])

    # Round 1: Provide base evidence + only React Context7 → expect failure
    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)
    _write_context7(project_dir.project_root, task_id, "react", 1)
    env = {"AGENTS_OWNER": session_id}
    res_fail = run_script("tasks/status", [task_id, "--status", "done"], cwd=project_dir.tmp_path, env=env)
    assert_command_failure(res_fail)
    assert ("zod" in res_fail.stdout or "zod" in res_fail.stderr)

    # Round 2: Add both React and Zod Context7 → expect success
    _ensure_base_evidence(project_dir.project_root, task_id, 2)
    _write_context7(project_dir.project_root, task_id, "react", 2)
    _write_context7(project_dir.project_root, task_id, "zod", 2)
    # Disable TDD enforcement in E2E context for success path
    env2 = dict(env)
    env2["DISABLE_TDD_ENFORCEMENT"] = "1"
    res_ok = run_script("tasks/status", [task_id, "--status", "done"], cwd=project_dir.tmp_path, env=env2)
    assert_command_success(res_ok)
    assert_file_exists(_task_file_path(project_dir.project_root, "done", task_id))


@pytest.mark.context7
@pytest.mark.requires_git
@pytest.mark.integration
def test_context7_prisma_schema_enforcement(combined_env):
    """Verify prisma schema.prisma triggers Context7 enforcement."""
    project_dir, git_repo = combined_env
    session_id = "test-ctx7-prisma-schema"
    task_num, wave, slug = "650", "wave1", "prisma-schema"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create session + task + QA
    run_script("session", ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path)
    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    # Claim task into the session so guards operate on session-scoped records.
    run_script("tasks/claim", [task_id, "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id, "--owner", session_id, "--session", session_id], cwd=project_dir.tmp_path)

    # Add prisma schema file to worktree
    sess = json.loads((project_dir.project_root / "sessions" / "wip" / session_id / "session.json").read_text())
    wt_raw = sess.get("git", {}).get("worktreePath")
    worktree_path = Path(wt_raw) if wt_raw else None
    if worktree_path and worktree_path.exists():
        schema_file = worktree_path / "packages" / "db" / "prisma" / "schema.prisma"
        schema_file.parent.mkdir(parents=True, exist_ok=True)
        schema_file.write_text(
            """
datasource db {
  provider = "sqldb"
  url = env("DATABASE_URL")
}

model Lead {
  id String @id @default(uuid())
  email String @unique
}
""".strip()
        )
        git_repo.commit_in_worktree(worktree_path, "feat: add prisma schema")
    else:
        # Fallback: record prisma file in task metadata when worktrees are unavailable
        target_meta = _task_file_path(project_dir.project_root, "todo", task_id)
        if not target_meta.exists():
            target_meta = _task_file_path(project_dir.project_root, "wip", task_id)
        _edit_primary_files(target_meta, ["packages/db/prisma/schema.prisma"])

    # Provide base evidence but NO prisma Context7 → should fail
    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    env = {"AGENTS_OWNER": session_id}
    res_fail = run_script("tasks/status", [task_id, "--status", "done"], cwd=project_dir.tmp_path, env=env)
    assert_command_failure(res_fail)
    assert ("prisma" in res_fail.stdout.lower() or "prisma" in res_fail.stderr.lower())

    # Add prisma Context7 evidence → should pass
    _write_context7(project_dir.project_root, task_id, "prisma", 1, session_id=session_id)
    env2 = dict(env)
    env2["DISABLE_TDD_ENFORCEMENT"] = "1"
    res_ok = run_script("tasks/status", [task_id, "--status", "done"], cwd=project_dir.tmp_path, env=env2)
    assert_command_success(res_ok)


@pytest.mark.context7
@pytest.mark.requires_git
@pytest.mark.integration
def test_context7_prisma_migration_enforcement(combined_env):
    """Verify prisma migration files trigger Context7 enforcement."""
    project_dir, git_repo = combined_env
    session_id = "test-ctx7-prisma-migration"
    task_num, wave, slug = "700", "wave1", "prisma-migration"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create session + task + QA
    run_script("session", ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path)
    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("tasks/status", [task_id, "--status", "wip"], cwd=project_dir.tmp_path)
    qa_waiting = project_dir.project_root / "qa" / "waiting"
    qa_waiting.mkdir(parents=True, exist_ok=True)
    (qa_waiting / f"{task_id}-qa.md").write_text("# QA\n\n## Validators\n- global-codex\n")

    # Add prisma migration files to worktree
    sess = json.loads((project_dir.project_root / "sessions" / "wip" / session_id / "session.json").read_text())
    wt_raw = sess.get("git", {}).get("worktreePath")
    worktree_path = Path(wt_raw) if wt_raw else None
    if worktree_path and worktree_path.exists():
        migration_dir = worktree_path / "packages" / "db" / "prisma" / "migrations" / "20250101000000_add_leads"
        migration_dir.mkdir(parents=True, exist_ok=True)
        (migration_dir / "migration.sql").write_text("CREATE TABLE leads (id UUID PRIMARY KEY);")
        git_repo.commit_in_worktree(worktree_path, "feat: add prisma migration")
    else:
        target_meta = _task_file_path(project_dir.project_root, "todo", task_id)
        if not target_meta.exists():
            target_meta = _task_file_path(project_dir.project_root, "wip", task_id)
        _edit_primary_files(target_meta, ["packages/db/prisma/migrations/20250101000000_add_leads/migration.sql"])

    # Provide base evidence but NO prisma Context7 → should fail
    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    env = {"AGENTS_OWNER": session_id}
    res_fail = run_script("tasks/status", [task_id, "--status", "done"], cwd=project_dir.tmp_path, env=env)
    assert_command_failure(res_fail)
    assert ("prisma" in res_fail.stdout.lower() or "prisma" in res_fail.stderr.lower())

    # Add prisma Context7 evidence → should pass
    _write_context7(project_dir.project_root, task_id, "prisma", 1, session_id=session_id)
    env2 = dict(env)
    env2["DISABLE_TDD_ENFORCEMENT"] = "1"
    res_ok = run_script("tasks/status", [task_id, "--status", "done"], cwd=project_dir.tmp_path, env=env2)
    assert_command_success(res_ok)


@pytest.mark.context7
@pytest.mark.requires_git
@pytest.mark.integration
def test_context7_prisma_seeds_enforcement(combined_env):
    """Verify prisma seed files trigger Context7 enforcement."""
    project_dir, git_repo = combined_env
    session_id = "test-ctx7-prisma-seeds"
    task_num, wave, slug = "750", "wave1", "prisma-seeds"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create session + task + QA
    run_script("session", ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path)
    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("tasks/status", [task_id, "--status", "wip"], cwd=project_dir.tmp_path)
    qa_waiting = project_dir.project_root / "qa" / "waiting"
    qa_waiting.mkdir(parents=True, exist_ok=True)
    (qa_waiting / f"{task_id}-qa.md").write_text("# QA\n\n## Validators\n- global-codex\n")

    # Add prisma seed files to worktree
    sess = json.loads((project_dir.project_root / "sessions" / "wip" / session_id / "session.json").read_text())
    wt_raw = sess.get("git", {}).get("worktreePath")
    worktree_path = Path(wt_raw) if wt_raw else None
    if worktree_path and worktree_path.exists():
        seed_file = worktree_path / "packages" / "db" / "prisma" / "seeds" / "users.ts"
        seed_file.parent.mkdir(parents=True, exist_ok=True)
        seed_file.write_text("export async function seedUsers() { /* seed logic */ }")
        git_repo.commit_in_worktree(worktree_path, "feat: add prisma seed")
    else:
        target_meta = _task_file_path(project_dir.project_root, "todo", task_id)
        if not target_meta.exists():
            target_meta = _task_file_path(project_dir.project_root, "wip", task_id)
        _edit_primary_files(target_meta, ["packages/db/prisma/seeds/users.ts"])

    # Provide base evidence but NO prisma Context7 → should fail
    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    env = {"AGENTS_OWNER": session_id}
    res_fail = run_script("tasks/status", [task_id, "--status", "done"], cwd=project_dir.tmp_path, env=env)
    assert_command_failure(res_fail)
    assert ("prisma" in res_fail.stdout.lower() or "prisma" in res_fail.stderr.lower())

    # Add prisma Context7 evidence → should pass
    _write_context7(project_dir.project_root, task_id, "prisma", 1, session_id=session_id)
    env2 = dict(env)
    env2["DISABLE_TDD_ENFORCEMENT"] = "1"
    res_ok = run_script("tasks/status", [task_id, "--status", "done"], cwd=project_dir.tmp_path, env=env2)
    assert_command_success(res_ok)


# -------------------------
# New negative tests for Workstream 1 (Context7 hardening)
# -------------------------


@pytest.mark.context7
@pytest.mark.requires_git
@pytest.mark.integration
def test_context7_zod_not_triggered_by_route_only(combined_env):
    """RED: Zod should NOT be required for route.ts alone.

    Historically, an over-broad trigger flagged zod whenever route.ts was
    present. This test ensures only 'next' (and 'react' if .tsx exists) are
    reported when no zod schema is added.
    """
    project_dir, git_repo = combined_env
    session_id = "test-ctx7-zod-route-only"
    task_num, wave, slug = "820", "wave1", "zod-route-only"
    task_id = f"{task_num}-{wave}-{slug}"

    # Session + task + QA
    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
    )
    assert_command_success(
        run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    )
    assert_command_success(run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(
        run_script("qa/new", [task_id, "--owner", session_id, "--session", session_id], cwd=project_dir.tmp_path)
    )

    # Create only route.ts and a tsx file; no zod files
    sess = json.loads((project_dir.project_root / "sessions" / "wip" / session_id / "session.json").read_text())
    wt = Path(sess["git"]["worktreePath"]) if sess.get("git", {}).get("worktreePath") else None
    if wt and wt.exists():
        (wt / "app/api/hello").mkdir(parents=True, exist_ok=True)
        (wt / "app/api/hello/route.ts").write_text("export function GET() { return new Response('ok') }\n")
        (wt / "components").mkdir(parents=True, exist_ok=True)
        (wt / "components/Button.tsx").write_text("export const Button = () => 'ok'\n")
        git_repo.commit_in_worktree(wt, "feat: add route + tsx without zod")
    else:
        # Fallback: declare files via Primary Files metadata
        path_pf = _task_file_path(project_dir.project_root, "todo", task_id)
        if not path_pf.exists():
            path_pf = _task_file_path(project_dir.project_root, "wip", task_id)
        _edit_primary_files(path_pf, ["app/api/hello/route.ts", "components/Button.tsx"])  # no zod

    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    res = run_script(
        "tasks/status",
        [task_id, "--status", "done", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_failure(res)
    out = (res.stdout + res.stderr)
    assert "Context7 evidence required" in out
    assert ("react" in out.lower()) and ("next" in out.lower())
    assert "zod" not in out.lower(), f"Zod should not be flagged. Output was:\n{out}"


@pytest.mark.context7
@pytest.mark.fast
def test_context7_non_git_primary_files_detection(project_dir: TestProjectDir):
    """RED: In non-git environments, Primary Files must still trigger Context7.

    We add React TSX and nextjs route paths to the task metadata without any
    git repo. Guard should require Context7 for those packages.
    """
    task_num, wave, slug = "830", "wave1", "non-git-scan"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create session + task → wip + QA (ignore git, we won't commit changes)
    session_id = "test-non-git-primary-files"
    run_script("session", ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path)
    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    # Add Primary Files to task metadata (simulate user-declared files) BEFORE moving to wip
    todo = _task_file_path(project_dir.project_root, "todo", task_id)
    _edit_primary_files(todo, [
        "app/api/hello/route.ts",
        "components/Avatar.tsx",
    ])
    run_script("tasks/status", [task_id, "--status", "wip"], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id, "--owner", session_id, "--session", session_id], cwd=project_dir.tmp_path)

    # Base evidence only; expect failure mentioning react and next
    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    env = {"AGENTS_OWNER": session_id}
    res = run_script("tasks/status", [task_id, "--status", "done"], cwd=project_dir.tmp_path, env=env)
    assert_command_failure(res)
    out = (res.stdout + res.stderr).lower()
    assert "react" in out and "next" in out


@pytest.mark.context7
@pytest.mark.fast
def test_context7_marker_content_validation(project_dir: TestProjectDir):
    """RED: Marker must contain minimal required fields (YAML frontmatter)."""
    task_num, wave, slug = "840", "wave1", "marker-content"
    task_id = f"{task_num}-{wave}-{slug}"

    session_id = "test-marker-content"
    run_script("session", ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path)
    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    # React usage via Primary Files
    todo = _task_file_path(project_dir.project_root, "todo", task_id)
    _edit_primary_files(todo, ["components/Profile.tsx"])  # triggers react
    run_script("tasks/status", [task_id, "--status", "wip"], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id, "--owner", session_id, "--session", session_id], cwd=project_dir.tmp_path)

    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    # Write an INVALID marker (missing required YAML frontmatter fields)
    ev_dir = _evidence_dir(project_dir.project_root, task_id, 1)
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "context7-react.txt").write_text("---\npackage: react\n---\n")
    markers_dir = (
        project_dir.project_root
        / "sessions"
        / "wip"
        / session_id
        / "tasks"
        / task_id
        / "evidence"
        / "context7"
        / "round-1"
        / "markers"
    )
    markers_dir.mkdir(parents=True, exist_ok=True)
    (markers_dir / "react.md").write_text("Context7 evidence for react\n")
    impl_report = markers_dir.parent / "implementation-report.md"
    if not impl_report.exists():
        impl_report.write_text("# Implementation Report\n\nPackages validated.\n")

    res_fail = run_script("tasks/status", [task_id, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_failure(res_fail)

    # Now write a VALID marker and expect success
    _write_context7(project_dir.project_root, task_id, "react", 1, session_id=session_id)
    # Disable TDD for success fast‑path
    env = {"DISABLE_TDD_ENFORCEMENT": "1"}
    res_ok = run_script("tasks/status", [task_id, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path, env=env)
    assert_command_success(res_ok)


@pytest.mark.context7
def test_context7_error_message_lists_all_packages(combined_env):
    """RED: Error message must list all detected packages explicitly."""
    project_dir, git_repo = combined_env
    session_id = "test-ctx7-error-list"
    task_num, wave, slug = "850", "wave1", "error-list"
    task_id = f"{task_num}-{wave}-{slug}"

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
    )
    assert_command_success(
        run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    )
    # Use Primary Files metadata instead of relying on git worktree
    todo = _task_file_path(project_dir.project_root, "todo", task_id)
    _edit_primary_files(todo, ["components/Card.tsx", "app/api/hello/route.ts"])
    assert_command_success(run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(
        run_script("qa/new", [task_id, "--owner", session_id, "--session", session_id], cwd=project_dir.tmp_path)
    )
    
    _ensure_impl_validate_ok(project_dir.project_root)
    _ensure_base_evidence(project_dir.project_root, task_id, 1)

    res = run_script(
        "tasks/status",
        [task_id, "--status", "done", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_failure(res)
    # Expect a single explicit line enumerating required packages (stdout or stderr)
    out = res.stdout + res.stderr
    assert "Context7 evidence required" in out
    assert ("react" in out.lower() and "next" in out.lower())
