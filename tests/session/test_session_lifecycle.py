from __future__ import annotations

import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import unittest
from unittest import mock

from edison.core.session.config import SessionConfig

def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists() and current.name != ".edison":
            return current
        current = current.parent
    raise RuntimeError("Could not find repository root")

# Reuse repo-root and scripts dir logic from existing tests
REPO_ROOT = get_repo_root()
SCRIPTS_DIR = REPO_ROOT / ".edison" / "core"

if str(SCRIPTS_DIR) not in os.sys.path:

from edison.core import task  # type: ignore  # pylint: disable=wrong-import-position
from edison.core.session import manager as session_manager
from edison.core.session import store as session_store
from edison.core.session import graph as session_graph
from edison.core.session import recovery as session_recovery
from edison.core.utils.subprocess import run_with_timeout


class SessionLifecycleCriticalFixes(unittest.TestCase):
    """TDD for 4 critical session lifecycle issues.

    Each test sets up an isolated temp project under project_ROOT to avoid
    interfering with the real repository.
    """

    def setUp(self) -> None:
        self.repo_root = REPO_ROOT
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-session-lifecycle-tests-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

        # Minimal project layout
        pr = self.temp_root / ".project"
        (pr / "tasks" / "todo").mkdir(parents=True, exist_ok=True)
        (pr / "tasks" / "wip").mkdir(parents=True, exist_ok=True)
        (pr / "tasks" / "blocked").mkdir(parents=True, exist_ok=True)
        (pr / "tasks" / "done").mkdir(parents=True, exist_ok=True)
        (pr / "tasks" / "validated").mkdir(parents=True, exist_ok=True)
        (pr / "qa" / "waiting").mkdir(parents=True, exist_ok=True)
        (pr / "qa" / "todo").mkdir(parents=True, exist_ok=True)
        (pr / "qa" / "wip").mkdir(parents=True, exist_ok=True)
        (pr / "qa" / "done").mkdir(parents=True, exist_ok=True)
        (pr / "qa" / "validated").mkdir(parents=True, exist_ok=True)
        (pr / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)
        # Session directories use on-disk names; mapping keys are asserted separately
        (pr / "sessions" / "wip").mkdir(parents=True, exist_ok=True)
        (pr / "sessions" / "done").mkdir(parents=True, exist_ok=True)
        (pr / "sessions" / "validated").mkdir(parents=True, exist_ok=True)

        # Copy required templates and config for session creation
        shutil.copyfile(
            self.repo_root / ".agents" / "sessions" / "TEMPLATE.json",
            self.temp_root / ".agents" / "sessions" / "TEMPLATE.json"
            if (self.temp_root / ".agents" / "sessions").mkdir(parents=True, exist_ok=True) or True
            else self.temp_root / ".agents" / "sessions" / "TEMPLATE.json"
        )
        cfg_src = self.repo_root / ".agents" / "config.yml"
        if cfg_src.exists():
            cfg_dst_dir = self.temp_root / ".agents"
            cfg_dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cfg_src, cfg_dst_dir / "config.yml")

        # Environment for subprocess CLI invocations
        self.base_env = os.environ.copy()
        self.base_env.update({
            "project_ROOT": str(self.temp_root),
            "AGENTS_PROJECT_ROOT": str(self.temp_root),
            "PYTHONUNBUFFERED": "1",
        })

        self.session_script = SCRIPTS_DIR / "scripts" / "session"

    def run_cli(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = [str(a) for a in args]
        result = run_with_timeout(cmd, cwd=self.repo_root, env=self.base_env, capture_output=True, text=True)
        if check and result.returncode != 0:
            raise AssertionError(
                f"Command {' '.join(cmd)} failed ({result.returncode})\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        return result

    def _create_session(self, session_id: str = "tester") -> str:
        # Use CLI so environment scoping via project_ROOT is respected at import time
        self.run_cli([self.session_script, "new", "--session-id", session_id, "--owner", "tester", "--mode", "start"], check=True)
        return session_id

    # Issue 1.1: session verify broken (missing import os) and must transition state → 'closing'
    def test_verify_sets_state_closing(self) -> None:
        sid = self._create_session("sid-verify")
        # Run through the CLI to exercise the script import path and env handling
        result = self.run_cli([self.session_script, "verify", sid, "--phase", "closing"], check=False)
        # Expect success and the session JSON to reflect state='closing'
        self.assertEqual(result.returncode, 0, msg=f"verify failed: {result.stdout} {result.stderr}")
        initial_state = SessionConfig().get_initial_session_state()
        data = json.loads((self.temp_root / ".project" / "sessions" / initial_state / sid / "session.json").read_text())
        self.assertEqual(data.get("state"), "closing")

    # Issue 1.2: session complete must fail-closed when restore fails
    def test_complete_fails_when_restore_errors(self) -> None:
        sid = self._create_session("sid-complete-guard")
        # Seed a child task in session scope at tasks/done so verification passes
        initial_state = SessionConfig().get_initial_session_state()
        sess_dir = self.temp_root / ".project" / "sessions" / initial_state / sid
        task_rel = Path("tasks") / "done" / "t-123.md"
        task_path = sess_dir / task_rel
        task_path.parent.mkdir(parents=True, exist_ok=True)
        task_path.write_text("# t-123\n- **Owner:** tester\n- **Status:** done\n")

        # Update session JSON to include this child task
        sess_path = sess_dir / "session.json"
        data = json.loads(sess_path.read_text())
        data.setdefault("tasks", {})["t-123"] = {
            "recordId": "t-123",
            "status": "done",
            "owner": "tester",
            "parentId": "p-1",
            "childIds": [],
        }
        sess_path.write_text(json.dumps(data, indent=2) + "\n")

        # Lock the intended global destination to force a transactional_move failure
        dest_lock = self.temp_root / ".project" / "tasks" / "done" / "t-123.md.lock"
        dest_lock.parent.mkdir(parents=True, exist_ok=True)
        dest_lock.write_text("lock")

        # Run completion via CLI; expect non-zero and no validation promotion
        result = self.run_cli([self.session_script, "complete", sid], check=False)
        self.assertNotEqual(result.returncode, 0, msg=f"expected failure-closed, got success: {result.stdout} {result.stderr}")
        payload = json.loads(sess_path.read_text())
        self.assertNotEqual(payload.get("state"), "validated")
        self.assertNotEqual(payload.get("meta", {}).get("status"), "validated")

    # Issue 1.3: state model consistency between session-workflow.json and task.SESSION_DIRS
    def test_state_model_alignment(self) -> None:
        wf = json.loads((self.repo_root / ".agents" / "session-workflow.json").read_text())
        states_from_workflow = wf.get("session", {}).get("states") or wf.get("states")  # support either layout
        # Tasklib mapping keys represent the chosen model
        mapping_keys = list(task.SESSION_DIRS.keys())
        self.assertEqual(states_from_workflow, mapping_keys)

    # Issue 1.4: worktree failures must halt and not persist metadata
    def test_worktree_failure_halts_and_does_not_persist(self) -> None:
        # Create minimal session JSON manually (avoid library root coupling)
        sid = "sid-wt-fail"
        sess_dir = self.temp_root / ".project" / "sessions" / "wip" / sid
        sess_dir.mkdir(parents=True, exist_ok=True)
        sess_file = sess_dir / "session.json"
        payload = {
            "meta": {
                "sessionId": sid,
                "owner": "tester",
                "mode": "start",
                "status": "wip",
                "createdAt": "2025-01-01T00:00:00Z",
                "lastActive": "2025-01-01T00:00:00Z",
            },
            "tasks": {},
            "qa": {},
            "git": {},
            "activityLog": [{"timestamp": "2025-01-01T00:00:00Z", "message": "Session created"}],
        }
        sess_file.write_text(json.dumps(payload, indent=2) + "\n")
        # Set env before loading module so module-level constants (SESSION_DIRS) are correct
        prev_project = os.environ.get("project_ROOT")
        os.environ["project_ROOT"] = str(self.temp_root)
        try:
            from importlib.machinery import SourceFileLoader
            session_mod = SourceFileLoader("session_cli_mod", str(self.session_script)).load_module()  # type: ignore
        finally:
            if prev_project is None:
                os.environ.pop("project_ROOT", None)
            else:
                os.environ["project_ROOT"] = prev_project

        # Remove any pre-existing worktree to force creation path
        wt_path = self.repo_root / ".worktrees" / sid
        if wt_path.exists():
            shutil.rmtree(wt_path, ignore_errors=True)
        # Clear git metadata in session JSON so list_status would be the only writer
        sess_path = self.temp_root / ".project" / "sessions" / "wip" / sid / "session.json"
        payload0 = json.loads(sess_path.read_text())
        payload0["git"] = {}
        sess_path.write_text(json.dumps(payload0, indent=2) + "\n")

        # Patch subprocess.run inside the session module to simulate git present but worktree add failing
        def fake_run(cmd, cwd=None, capture_output=False, text=False, check=False):  # type: ignore[no-redef]
            cmd_str = " ".join(cmd)
            class R:  # Minimal CompletedProcess-like
                def __init__(self, rc: int, out: str = ""):
                    self.returncode = rc
                    self.stdout = out
                    self.stderr = ""
            if cmd[:3] == ["git", "rev-parse", "--is-inside-work-tree"]:
                return R(0, "true\n")
            if cmd[:2] == ["git", "branch"]:
                return R(0, "\n")
            if cmd[:2] == ["git", "worktree"] and "add" in cmd:
                raise subprocess.CalledProcessError(1, cmd, output="", stderr="simulated failure")
            return R(0, "")

        with mock.patch.object(session_mod.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(session_mod, "is_git_repository", return_value=True):
            # Ensure in-process imports honor the sandbox root for Edison libs
            prev_project = os.environ.get("project_ROOT")
            prev_agents = os.environ.get("AGENTS_PROJECT_ROOT")
            try:
                os.environ["project_ROOT"] = str(self.temp_root)
                os.environ["AGENTS_PROJECT_ROOT"] = str(self.temp_root)
                import importlib
                import edison.core.paths.resolver as paths  # type: ignore
                paths._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
                importlib.reload(session_mod.task)  # type: ignore[attr-defined]
                importlib.reload(session_mod.session_manager)  # type: ignore[attr-defined]
                importlib.reload(session_mod.session_store)  # type: ignore[attr-defined]
                # Update references in session_mod to point to reloaded modules
                session_mod.load_session = session_mod.session_manager.get_session
                session_mod.session_store = session_mod.session_store
                session_mod.SESSION_DIRS = session_mod.task.SESSION_DIRS
                with self.assertRaises(SystemExit) as ctx:
                    session_mod.list_status(sid, as_json=True)
                self.assertNotEqual(ctx.exception.code, 0)
            finally:
                if prev_project is None:
                    os.environ.pop("project_ROOT", None)
                else:
                    os.environ["project_ROOT"] = prev_project
                if prev_agents is None:
                    os.environ.pop("AGENTS_PROJECT_ROOT", None)
                else:
                    os.environ["AGENTS_PROJECT_ROOT"] = prev_agents

        # Ensure git metadata not persisted on failure
        payload = json.loads((self.temp_root / ".project" / "sessions" / "wip" / sid / "session.json").read_text())
        git_meta = payload.get("git", {}) if isinstance(payload.get("git", {}), dict) else {}
        self.assertFalse(git_meta.get("worktreePath"))


if __name__ == "__main__":
    unittest.main()