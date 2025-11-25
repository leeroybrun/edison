from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from edison.core.utils.subprocess import run_with_timeout

REPO_ROOT = Path(__file__).resolve().parents[4]


class SessionNextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-session-next-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))
        # Mirror minimal .project layout
        for d in ["tasks/todo", "tasks/wip", "qa/waiting", "qa/todo", "qa/wip", "qa/validation-evidence", "sessions/wip"]:
            (self.temp_root / ".project" / d).mkdir(parents=True, exist_ok=True)
        # Ensure Edison canonical session template location exists
        agents_sessions = self.temp_root / ".agents" / "sessions"
        agents_sessions.mkdir(parents=True, exist_ok=True)
        # Copy templates and config used by session script
        shutil.copyfile(REPO_ROOT / ".agents" / "sessions" / "TEMPLATE.json", agents_sessions / "TEMPLATE.json")
        shutil.copyfile(REPO_ROOT / ".project" / "qa" / "TEMPLATE.md", self.temp_root / ".project" / "qa" / "TEMPLATE.md")
        cfg_src = REPO_ROOT / ".agents" / "config.yml"
        if cfg_src.exists():
            cfg_dst = self.temp_root / ".agents" / "config.yml"
            cfg_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cfg_src, cfg_dst)

        self.env = os.environ.copy()
        self.env.update({"project_ROOT": str(self.temp_root), "project_OWNER": "claude-pid-999"})

    def run_cli(self, *parts: str) -> subprocess.CompletedProcess[str]:
        return run_with_timeout(list(parts), cwd=REPO_ROOT, env=self.env, capture_output=True, text=True)

    def test_next_suggests_missing_qa_and_promotion(self) -> None:
        # Create session
        res = self.run_cli(str(REPO_ROOT / "scripts" / "session"), "new")
        self.assertEqual(res.returncode, 0, f"stderr: {res.stderr}\nstdout: {res.stdout}")
        # Create a wip task without QA
        task_id = "200-wave1-demo"
        (self.temp_root / ".project" / "tasks" / "wip" / f"{task_id}.md").write_text(
            """
            # 200-wave1-demo
            - **Task Type:** api-route
            - **Status:** wip
            - **Primary Files / Areas:**
              - app/api/leads/route.ts
            """
        )
        # Register task in session scope directly (bypass file metadata requirements)
        res = self.run_cli(str(REPO_ROOT / "scripts" / "session"), "add", "claude-pid-999", "task", task_id, "--owner", "claude", "--status", "wip")
        self.assertEqual(res.returncode, 0, res.stderr)
        # Ask session next for actions
        res = self.run_cli(str(REPO_ROOT / "scripts" / "session"), "next", "claude-pid-999", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout or "{}")
        action_ids = [a["id"] for a in payload.get("actions", [])]
        self.assertIn("qa.create", action_ids, payload)

    def test_parent_unblocks_and_promotes_after_children_ready(self) -> None:
        # Create session
        # Use the default owner from setUp (claude-pid-999)
        # Create session
        # Use the default owner from setUp (claude-pid-999)
        res = self.run_cli(str(REPO_ROOT / "scripts" / "session"), "new")
        self.assertEqual(res.returncode, 0, f"stderr: {res.stderr}\nstdout: {res.stdout}")

        parent = "201-wave2-parent"
        child = "201.1-wave2-child"

        # Seed task files
        tasks_root = self.temp_root / ".project" / "tasks"
        qa_root = self.temp_root / ".project" / "qa"
        (tasks_root / "wip" / f"{parent}.md").write_text(
            f"# {parent}\n- **Status:** wip\n- **Owner:** claude\n- **Session Info:**\n  - **Claimed At:** now\n  - **Last Active:** now\n"
        )
        (tasks_root / "done").mkdir(parents=True, exist_ok=True)
        (tasks_root / "done" / f"{child}.md").write_text(
            f"# {child}\n- **Status:** validated\n- **Owner:** claude\n"
        )

        # Determine created session id
        from edison.core.session.config import SessionConfig
        init_state = SessionConfig().get_initial_session_state()
        sessions_dir = self.temp_root / ".project" / "sessions" / init_state
        sess_files = sorted([p for p in sessions_dir.glob("*/session.json")])
        if not sess_files:
            print(f"DEBUG: session new stdout: {res.stdout}")
            print(f"DEBUG: session new stderr: {res.stderr}")
            print(f"DEBUG: sessions_dir content: {list(sessions_dir.glob('**/*'))}")
        self.assertTrue(sess_files, "No session file found after session new")
        session_id = sess_files[0].parent.name

        # Register both in session and link
        r1 = self.run_cli(str(REPO_ROOT / "scripts" / "session"), "add", session_id, "task", parent, "--owner", "claude", "--status", "blocked")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        r2 = self.run_cli(str(REPO_ROOT / "scripts" / "session"), "add", session_id, "task", child, "--owner", "claude", "--status", "validated")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        r3 = self.run_cli(str(REPO_ROOT / "scripts" / "tasks" / "link"), parent, child, "--session", session_id)
        self.assertEqual(r3.returncode, 0, r3.stderr)

        # Evidence present for parent
        ev = qa_root / "validation-evidence" / parent / "round-1"
        ev.mkdir(parents=True, exist_ok=True)
        for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt", "implementation-report.json"]:
            (ev / name).write_text("ok\n")

        # Ask for next actions
        res2 = self.run_cli(str(REPO_ROOT / "scripts" / "session"), "next", session_id, "--json")
        self.assertEqual(res2.returncode, 0, res2.stderr)
        data = json.loads(res2.stdout or "{}")
        action_ids = [a.get("id") for a in data.get("actions", [])]
        # Expect unblock suggestion; promote to done will appear on the next cycle after unblocking
        self.assertIn("task.unblock.wip", action_ids, data)

    def test_task_promote_done_includes_guard_preview(self) -> None:
        """session next should annotate task.promote.done with guard preview."""
        # Create session
        res = self.run_cli(str(REPO_ROOT / "scripts" / "session"), "new")
        self.assertEqual(res.returncode, 0, f"stderr: {res.stderr}\nstdout: {res.stdout}")

        # Determine created session id
        sessions_dir = self.temp_root / ".project" / "sessions" / "draft"
        sess_files = sorted([p for p in sessions_dir.glob("*/session.json")])
        if not sess_files:
            print(f"DEBUG: session new stdout: {res.stdout}")
            print(f"DEBUG: session new stderr: {res.stderr}")
            print(f"DEBUG: sessions_dir content: {list(sessions_dir.glob('**/*'))}")
        self.assertTrue(sess_files, "No session file found after session new")
        session_id = sess_files[0].parent.name

        # Seed a wip task with evidence so that task.promote.done is suggested
        task_id = "300-wave1-guard-preview"
        tasks_root = self.temp_root / ".project" / "tasks"
        qa_root = self.temp_root / ".project" / "qa"
        (tasks_root / "wip").mkdir(parents=True, exist_ok=True)
        (tasks_root / "wip" / f"{task_id}.md").write_text(
            f"# {task_id}\n- **Status:** wip\n- **Owner:** claude\n"
        )

        # Register task in session scope as wip
        res_add = self.run_cli(
            str(REPO_ROOT / "scripts" / "session"),
            "add",
            session_id,
            "task",
            task_id,
            "--owner",
            "claude",
            "--status",
            "wip",
        )
        self.assertEqual(res_add.returncode, 0, res_add.stderr)

        # Provide minimal automation evidence including implementation report
        ev = qa_root / "validation-evidence" / task_id / "round-1"
        ev.mkdir(parents=True, exist_ok=True)
        (ev / "implementation-report.json").write_text("{}", encoding="utf-8")
        for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
            (ev / name).write_text("ok\n", encoding="utf-8")

        # Ask for next actions
        res_next = self.run_cli(
            str(REPO_ROOT / "scripts" / "session"),
            "next",
            session_id,
            "--json",
        )
        self.assertEqual(res_next.returncode, 0, res_next.stderr)
        payload = json.loads(res_next.stdout or "{}")
        actions = payload.get("actions", [])
        promote_actions = [a for a in actions if a.get("id") == "task.promote.done"]
        self.assertTrue(promote_actions, f"Expected task.promote.done action in {actions}")
        guard = promote_actions[0].get("guard") or {}
        self.assertEqual(guard.get("from"), "wip")
        self.assertEqual(guard.get("to"), "done")
        self.assertEqual(guard.get("status"), "allowed")


if __name__ == "__main__":
    unittest.main()