"""Tests for standardizing stderr usage across CLIs.

Focus: --json mode must emit pure JSON on stdout.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from edison.core.utils.subprocess import run_with_timeout


REPO_ROOT = Path(__file__).resolve().parents[2]


class TestStdErrConventions(unittest.TestCase):
    def setUp(self) -> None:
        self.project_root = REPO_ROOT
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-stderr-tests-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))
        (self.temp_root / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)
        (self.temp_root / ".project" / "tasks" / "wip").mkdir(parents=True, exist_ok=True)

        self.base_env = os.environ.copy()
        self.base_env.update({
            "AGENTS_PROJECT_ROOT": str(self.temp_root),
            "PYTHONUNBUFFERED": "1",
        })

    def _run(self, cmd: list[str|Path], check: bool = True) -> subprocess.CompletedProcess[str]:
        result = run_with_timeout([str(c) for c in cmd], cwd=self.project_root, env=self.base_env, capture_output=True, text=True)
        if check and result.returncode != 0:
            raise AssertionError(f"Command failed ({result.returncode})\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result

    def test_implementation_report_print_path_stdout_only(self) -> None:
        task_id = "stderr-conventions-1"
        # `session track start` is task-scoped and must fail closed when the task is missing.
        (self.temp_root / ".project" / "tasks" / "wip" / f"{task_id}.md").write_text(
            f"---\nid: {task_id}\ntitle: Stderr conventions\n---\n",
            encoding="utf-8",
        )
        res = self._run([
            sys.executable, "-m", "edison",
            "session", "track", "start",
            "--task", task_id,
            "--type", "implementation",
            "--model", "claude",
            "--json",
        ], check=False)

        self.assertEqual(res.returncode, 0, f"command failed: {res.stderr}\nSTDOUT:{res.stdout}")
        payload = json.loads(res.stdout)
        self.assertEqual(payload.get("taskId"), task_id)
        self.assertEqual(payload.get("type"), "implementation")
        out_path = Path(str(payload.get("path") or ""))
        self.assertEqual(out_path.name, "implementation-report.md")


if __name__ == "__main__":
    unittest.main()
