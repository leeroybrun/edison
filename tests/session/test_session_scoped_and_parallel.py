"""End-to-end tests for session-scoped tasks/qa and parallel implementers.

These tests exercise the real Python CLIs under `.agents/scripts/*` with no mocking.
They create a temporary `.project` work area via `project_ROOT` and verify:

- Claiming a task into a session moves it under `.project/sessions/wip/<sid>/tasks/...` and hides it from the global queues.
- QA briefs created with `qa/new` inside a session live under the session tree.
- `tasks/list` shows global-only by default and supports `--session <sid>`.
- Full parent validation with child tasks done (parallel implementers) and session completion restores files to global queues.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import textwrap
import unittest
from edison.core.utils.subprocess import run_with_timeout


REPO_ROOT = Path(__file__).resolve().parents[4]    # repository root
SCRIPTS_ROOT = REPO_ROOT / "scripts"               # use top-level wrappers


def scripts_path(*parts: object) -> Path:
    p = SCRIPTS_ROOT
    for part in parts:
        p = p / str(part)
    return p.resolve()


class SessionScopedWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-session-scoped-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

        # Minimal .project layout and templates
        for d in [
            ".project/tasks/todo",
            ".project/tasks/wip",
            ".project/tasks/done",
            ".project/tasks/validated",
            ".project/qa/waiting",
            ".project/qa/todo",
            ".project/qa/wip",
            ".project/qa/done",
            ".project/qa/validated",
            ".project/qa/validation-evidence",
            ".project/sessions/draft",
            ".project/sessions/active",
            ".project/sessions/done",
            ".project/sessions/closing",
            ".project/sessions/validated",
            ".agents/sessions",
        ]:
            (self.temp_root / d).mkdir(parents=True, exist_ok=True)

        # Copy templates referenced by CLIs (Edison canonical location: .agents/sessions)
        shutil.copyfile(REPO_ROOT / ".agents" / "sessions" / "TEMPLATE.json", self.temp_root / ".agents" / "sessions" / "TEMPLATE.json")
        shutil.copyfile(REPO_ROOT / ".project" / "qa" / "TEMPLATE.md", self.temp_root / ".project" / "qa" / "TEMPLATE.md")
        shutil.copyfile(REPO_ROOT / ".project" / "tasks" / "TEMPLATE.md", self.temp_root / ".project" / "tasks" / "TEMPLATE.md")
        
        # Copy core config to temp root so ConfigManager finds them
        core_config_src = REPO_ROOT / ".edison" / "core" / "config"
        core_config_dst = self.temp_root / ".edison" / "core" / "config"
        core_config_dst.mkdir(parents=True, exist_ok=True)
        for cfg in ["defaults.yaml", "session.yaml", "state-machine.yaml"]:
            if (core_config_src / cfg).exists():
                shutil.copyfile(core_config_src / cfg, core_config_dst / cfg)

        # Minimal Context7 config expected by tasks/ready guards (YAML overlay)
        vcfg_dir = self.temp_root / ".agents" / "config"
        vcfg_dir.mkdir(parents=True, exist_ok=True)
        vcfg_yaml = vcfg_dir / "validators.yml"
        if not vcfg_yaml.exists():
            vcfg_yaml.write_text(
                "postTrainingPackages:\n"
                "  placeholder:\n"
                "    triggers: [\"__never__\"]\n"
                "    context7Topics: []\n",
                encoding="utf-8",
            )

        self.env = os.environ.copy()
        self.env.update({
            "project_ROOT": str(self.temp_root),
            "AGENTS_PROJECT_ROOT": str(self.temp_root),
            "project_OWNER": "claude-pid-12345",
            "PYTHONUNBUFFERED": "1",
            "DISABLE_TDD_ENFORCEMENT": "1",
        })

        # CLI entry paths under .agents/scripts
        self.session_cli = scripts_path("session")
        self.tasks_claim = scripts_path("tasks", "claim")
        self.tasks_status = scripts_path("tasks", "status")
        self.tasks_list = scripts_path("tasks", "list")
        self.tasks_new = scripts_path("tasks", "new")
        self.tasks_link = scripts_path("tasks", "link")
        self.qa_new = scripts_path("qa", "new")
        self.qa_promote = scripts_path("qa", "promote")

    def run_cli(self, *argv: str | Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = [str(argv[0]), *[str(p) for p in argv[1:]]]
        res = run_with_timeout(cmd, cwd=SCRIPTS_ROOT, env=self.env, capture_output=True, text=True)
        if check and res.returncode != 0:
            raise AssertionError(f"Command failed ({res.returncode})\nCMD: {' '.join(cmd)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
        return res

    def _seed_task(self, task_id: str, status: str = "todo") -> Path:
        content = textwrap.dedent(
            f"""
            # {task_id}
            - **Task ID:** {task_id}
            - **Priority Slot:** {task_id.split('-')[0]}
            - **Wave:** {task_id.split('-')[1]}
            - **Owner:** _unassigned_
            - **Status:** {status}
            - **Created:** 2025-11-13
            - **Session Info:**
              - **Claimed At:** _unassigned_
              - **Last Active:** _unassigned_
              - **Continuation ID:** _none_
              - **Primary Model:** _unassigned_
            """
        ).strip() + "\n"
        dest = self.temp_root / ".project" / "tasks" / status / f"{task_id}.md"
        dest.write_text(content)
        return dest

    def _evidence_ok(self, task_id: str, include_impl_report: bool = True) -> None:
        ev = self.temp_root / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        ev.mkdir(parents=True, exist_ok=True)
        for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
            (ev / name).write_text("RUNNER: tasks/ready\nEXIT_CODE: 0\n")
        if include_impl_report:
            report = {
                "taskId": task_id,
                "round": 1,
                "implementationApproach": "orchestrator-direct",
                "primaryModel": "claude",
                "completionStatus": "complete",
                "followUpTasks": [],
                "notesForValidator": "ok",
                "tracking": {
                    "startedAt": "1970-01-01T00:00:00Z",
                    "processId": 1234,
                    "completedAt": "t2",
                },
            }
            (ev / "implementation-report.json").write_text(json.dumps(report, indent=2))

    def _latest_round(self, task_id: str) -> Path:
        ev_root = self.temp_root / ".project" / "qa" / "validation-evidence" / task_id
        rounds = sorted([p for p in ev_root.glob("round-*") if p.is_dir()], key=lambda p: p.name)
        return rounds[-1]

    def test_session_scoped_claim_and_qa_flow(self) -> None:
        # Create session
        res = self.run_cli(self.session_cli, "new")
        self.assertEqual(res.returncode, 0, res.stderr)
        
        # Debug: list sessions dir
        sessions_root = self.temp_root / ".project" / "sessions"
        print(f"DEBUG: sessions root contents: {list(sessions_root.glob('**/*'))}")
        
        sess_file = next((self.temp_root / ".project" / "sessions" / "draft").glob("*/*.json"))
        session_id = sess_file.parent.name
        
        # Start session to move it to active (test expects active paths)
        self.run_cli(self.session_cli, "start", session_id)

        # Seed a task globally in todo/
        task_id = "150-wave1-demo"
        self._seed_task(task_id, status="todo")

        # Claim into session to wip; claiming should also relocate under the session tree
        self.run_cli(self.tasks_claim, task_id, "--status", "wip", "--session", session_id)

        session_task_path = self.temp_root / ".project" / "sessions" / "active" / session_id / "tasks" / "wip" / f"{task_id}.md"
        self.assertTrue(session_task_path.exists(), "Task should be relocated under the session tree when claimed")
        # Global queue should no longer contain the file
        self.assertFalse((self.temp_root / ".project" / "tasks" / "wip" / f"{task_id}.md").exists())

        # Create QA inside the session automatically
        self.run_cli(self.qa_new, task_id, "--session", session_id)
        session_qa_path = self.temp_root / ".project" / "sessions" / "active" / session_id / "qa" / "waiting" / f"{task_id}-qa.md"
        self.assertTrue(session_qa_path.exists(), "QA brief should be created under session qa/waiting")

        # tasks/list should not show session items by default
        out = self.run_cli(self.tasks_list, "--format", "json").stdout
        items = json.loads(out)
        self.assertTrue(all("/sessions/" not in rec["path"] for rec in items), "Default list must exclude session-scoped records")

        # tasks/list --session should show only session items
        out2 = self.run_cli(self.tasks_list, "--session", session_id, "--format", "json").stdout
        items2 = json.loads(out2)
        paths2 = [rec["path"] for rec in items2]
        self.assertTrue(any(f"/sessions/active/{session_id}/tasks/wip/{task_id}.md" in p for p in paths2))

        # Complete implementation for childless parent and validate end-to-end
        self._evidence_ok(task_id)
        self.run_cli(self.tasks_status, task_id, "--status", "done", "--session", session_id)
        self.run_cli(self.qa_promote, "--task", task_id, "--to", "todo", "--session", session_id)
        # Simulate validator approvals
        latest = self._latest_round(task_id)
        (latest / "bundle-approved.json").write_text("{\n  \"approved\": true\n}\n")
        self.run_cli(self.qa_promote, "--task", task_id, "--to", "wip", "--session", session_id)
        self.run_cli(self.qa_promote, "--task", task_id, "--to", "done", "--session", session_id)
        self.run_cli(self.tasks_status, task_id, "--status", "validated", "--session", session_id)

        # Complete session: files should be restored to global queues with final states
        self.run_cli(self.session_cli, "complete", session_id)
        self.assertTrue((self.temp_root / ".project" / "tasks" / "validated" / f"{task_id}.md").exists())
        self.assertTrue((self.temp_root / ".project" / "qa" / "done" / f"{task_id}-qa.md").exists())

    def test_parallel_implementers_parent_blocks_until_children_done(self) -> None:
        # Create session
        self.run_cli(self.session_cli, "new")
        session_id = next((self.temp_root / ".project" / "sessions" / "draft").glob("*/*.json")).parent.name
        
        # Start session
        self.run_cli(self.session_cli, "start", session_id)

        parent = "201-wave2-parent"
        # Seed parent in wip and claim into session (moves under session tree)
        self._seed_task(parent, status="wip")
        self.run_cli(self.tasks_claim, parent, "--status", "wip", "--session", session_id)
        self.run_cli(self.qa_new, parent, "--session", session_id)

        # Create two child tasks via tasks/new; link to parent; claim children
        child1 = "201.1-wave2-child-a"
        child2 = "201.2-wave2-child-b"
        for cid in (child1, child2):
            # Create globally in todo then claim into session (auto-move)
            self.run_cli(self.tasks_new, "--id", cid.split("-")[0], "--wave", "wave2", "--slug", "child-a" if cid.endswith("a") else "child-b", "--session", session_id)
            self.run_cli(self.tasks_claim, cid, "--status", "wip", "--session", session_id)
            self.run_cli(self.tasks_link, parent, cid, "--session", session_id)
            self.run_cli(self.qa_new, cid, "--session", session_id)  # child QA present but will not be validated

        # Attempt to move parent to done should fail until children are done
        self._evidence_ok(parent)
        bad = self.run_cli(self.tasks_status, parent, "--status", "done", "--session", session_id, check=False)
        self.assertNotEqual(bad.returncode, 0, bad.stdout + bad.stderr)
        self.assertIn("Child task", bad.stderr + bad.stdout)

        # Finish both children (wip -> done) with minimal evidence and QA left in waiting
        for cid in (child1, child2):
            self._evidence_ok(cid)
            self.run_cli(self.tasks_status, cid, "--status", "done", "--session", session_id)

        # Now parent can move to done, validators approve, and parent validates
        self.run_cli(self.tasks_status, parent, "--status", "done", "--session", session_id)
        self.run_cli(self.qa_promote, "--task", parent, "--to", "todo", "--session", session_id)
        latest = self._latest_round(parent)
        (latest / "bundle-approved.json").write_text("{\n  \"approved\": true\n}\n")
        self.run_cli(self.qa_promote, "--task", parent, "--to", "wip", "--session", session_id)
        self.run_cli(self.qa_promote, "--task", parent, "--to", "done", "--session", session_id)
        self.run_cli(self.tasks_status, parent, "--status", "validated", "--session", session_id)

        # Complete session, children remain global done, parent global validated
        self.run_cli(self.session_cli, "complete", session_id)
        self.assertTrue((self.temp_root / ".project" / "tasks" / "validated" / f"{parent}.md").exists())
        self.assertTrue((self.temp_root / ".project" / "tasks" / "done" / f"{child1}.md").exists())
        self.assertTrue((self.temp_root / ".project" / "tasks" / "done" / f"{child2}.md").exists())


if __name__ == "__main__":
    unittest.main()