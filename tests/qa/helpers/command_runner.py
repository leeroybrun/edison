"""Command execution helpers for QA tests after migration.

This wrapper routes QA commands to `.edison/core/scripts/qa/*` and delegates
other commands to core scripts under `.edison/core/scripts/`.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from edison.core.utils.subprocess import run_with_timeout
from edison.core.paths.resolver import PathResolver

_repo_root = PathResolver.resolve_project_root()


def _edison_script_path(script_name: str) -> Path:
    return _repo_root / ".edison" / "core" / "scripts" / script_name


def run_script(
    script_name: str,
    args: List[str],
    cwd: Path,
    check: bool = False,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Run a script, routing to new locations when needed.

    - `qa/*` → `.edison/core/scripts/qa/*`
    - `validators/validate` → `.edison/core/scripts/validators/validate`
    - `tasks/*` → `.edison/core/scripts/tasks/*`
    - `session` → emulate minimal `session new` behavior for tests
    - otherwise → resolve under `.edison/core/scripts/`
    """
    # Emulate minimal session CLI for tests
    if script_name == "session":
        # Very small emulation to support only `session new --session-id <sid> [--mode start]`
        sid = None
        it = iter(args)
        try:
            for a in it:
                if a == "--session-id":
                    sid = next(it)
        except StopIteration:
            pass
        if sid:
            sessions_dir = Path(cwd) / ".project" / "sessions" / "wip"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            now = __import__("datetime").datetime.utcnow().isoformat() + "Z"
            payload = {
                "meta": {"sessionId": sid, "createdAt": now, "lastActive": now},
                "tasks": {},
                "qa": {},
                "activityLog": [],
            }
            import json as _json
            (sessions_dir / f"{sid}.json").write_text(_json.dumps(payload, indent=2))
            cp = subprocess.CompletedProcess(["session", *args], 0, "", "")
            return cp
        # Fall through to legacy helper if we couldn't emulate

    # Emulate tasks/new
    if script_name == "tasks/new":
        # Parse CLI style args
        tid = None; wave = None; slug = None; sid = None
        it = iter(args)
        for a in it:
            if a == "--id":
                tid = next(it, None)
            elif a == "--wave":
                wave = next(it, None)
            elif a == "--slug":
                slug = next(it, None)
            elif a == "--session":
                sid = next(it, None)
        if tid and wave and slug:
            task_id = f"{tid}-{wave}-{slug}"
            content = "\n".join([
                f"# Task {task_id}",
                "",
                "- **Owner:** _unassigned_",
                f"- **Wave:** {wave}",
                "- **Status:** todo",
                "",
            ]) + "\n"
            global_path = Path(cwd) / ".project" / "tasks" / "todo" / f"{task_id}.md"
            global_path.parent.mkdir(parents=True, exist_ok=True)
            global_path.write_text(content)
            if sid:
                sess_path = Path(cwd) / ".project" / "sessions" / "wip" / sid / "tasks" / "todo" / f"{task_id}.md"
                sess_path.parent.mkdir(parents=True, exist_ok=True)
                sess_path.write_text(content)
            return subprocess.CompletedProcess(["tasks/new", *args], 0, "", "")
        return subprocess.CompletedProcess(["tasks/new", *args], 2, "", "Missing args for tasks/new\n")

    # Emulate tasks/link (session-scoped parent/child mapping only)
    if script_name == "tasks/link":
        parent = args[0] if args else None
        child = args[1] if len(args) > 1 else None
        sid = None
        it = iter(args[2:])
        for a in it:
            if a == "--session":
                sid = next(it, None)
        if parent and child and sid:
            sess = Path(cwd) / ".project" / "sessions" / "wip" / f"{sid}.json"
            try:
                import json
                data = json.loads(sess.read_text())
                tasks = data.setdefault("tasks", {})
                parent_entry = tasks.setdefault(parent, {})
                children = parent_entry.setdefault("children", [])
                if child not in children:
                    children.append(child)
                sess.write_text(json.dumps(data, indent=2))
                return subprocess.CompletedProcess(["tasks/link", *args], 0, "", "")
            except Exception as e:
                return subprocess.CompletedProcess(["tasks/link", *args], 1, "", str(e))
        return subprocess.CompletedProcess(["tasks/link", *args], 2, "", "Missing args for tasks/link\n")

    # Route QA commands
    if script_name.startswith("qa/"):
        script_path = _edison_script_path(script_name)
    elif script_name == "validators/validate":
        script_path = _edison_script_path("validators/validate")
    elif script_name.startswith("tasks/"):
        script_path = _edison_script_path(script_name)
    else:
        script_path = _edison_script_path(script_name)

    if script_path.exists():
        # Ensure QA template exists for qa/new
        if script_name == "qa/new":
            tpl = Path(cwd) / ".project" / "qa" / "TEMPLATE.md"
            if not tpl.exists():
                repo_tpl = _repo_root / ".project" / "qa" / "TEMPLATE.md"
                tpl.parent.mkdir(parents=True, exist_ok=True)
                if repo_tpl.exists():
                    tpl.write_text(repo_tpl.read_text())
                else:
                    tpl.write_text("# {TASK_ID}-qa\n\n- **Validator Owner:** _unassigned_\n- **Status:** waiting\n")
        # Choose interpreter based on shebang or file type
        interp = "python3"
        try:
            first_line = script_path.read_text().splitlines()[0]
        except Exception:
            first_line = ""
        if first_line.startswith("#!") and ("bash" in first_line or "sh" in first_line):
            interp = "bash"
        elif script_path.suffix == "" and "set -euo pipefail" in script_path.read_text()[:200]:
            interp = "bash"
        cmd = [interp, str(script_path), *args]
        test_env = os.environ.copy()
        if env:
            test_env.update(env)
        # Tell CLI scripts to treat `cwd` as the project root for test isolation
        test_env["AGENTS_PROJECT_ROOT"] = str(cwd)
        return run_with_timeout(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
            env=test_env,
        )

    # Fallback: return failure if script not found
    return subprocess.CompletedProcess([script_name, *args], 127, "", f"Script not found: {script_name}\n")


# Re-export assertion helpers from original module
def assert_command_success(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, (
        f"Command failed with exit code {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


def assert_command_failure(result: subprocess.CompletedProcess) -> None:
    assert result.returncode != 0, (
        f"Command unexpectedly succeeded\nSTDOUT:\n{result.stdout}"
    )


def assert_output_contains(result: subprocess.CompletedProcess, expected: str, in_stderr: bool = False) -> None:
    output = result.stderr if in_stderr else result.stdout
    assert expected in output, (
        f"Expected '{expected}' not found in {'stderr' if in_stderr else 'stdout'}\nOutput:\n{output}"
    )


def assert_error_contains(result: subprocess.CompletedProcess, expected: str) -> None:
    assert expected in result.stderr, (
        f"Expected error '{expected}' not found in stderr\nSTDERR:\n{result.stderr}"
    )


def assert_json_output(result: subprocess.CompletedProcess) -> dict:
    import json
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"Command output is not valid JSON: {e}\nOutput:\n{result.stdout}"
        )
