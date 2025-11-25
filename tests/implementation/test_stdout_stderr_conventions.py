"""Tests for standardizing stderr usage across CLIs.

Focus: scripts/implementation/report should emit logs to stderr and allow
machine-readable stdout via --print-path (path only).
"""
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
SCRIPTS_DIR = REPO_ROOT / ".edison" / "core" / "scripts"


class StdErrConventionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = REPO_ROOT
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-stderr-tests-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))
        self.project_root = self.temp_root / ".project"
        self.qa_root = self.project_root / "qa" / "validation-evidence"
        (self.qa_root).mkdir(parents=True, exist_ok=True)

        self.base_env = os.environ.copy()
        self.base_env.update({
            "project_ROOT": str(self.temp_root),
            "PYTHONUNBUFFERED": "1",
        })

        self.impl_report_script = SCRIPTS_DIR / "implement" / "report"

    def _run(self, cmd: list[str|Path], check: bool = True) -> subprocess.CompletedProcess[str]:
        result = run_with_timeout([str(c) for c in cmd], cwd=self.repo_root, env=self.base_env, capture_output=True, text=True)
        if check and result.returncode != 0:
            raise AssertionError(f"Command failed ({result.returncode})\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result

    def test_implementation_report_print_path_stdout_only(self) -> None:
        task_id = "stderr-conventions-1"
        # Minimum required fields to pass schema validation
        res = self._run([
            "python3", self.impl_report_script,
            "--task", task_id,
            "--status", "complete",
            "--notes", "ok",
            "--approach", "orchestrator-direct",
            "--model", "claude",
            "--delegation-compliance", "false",
            "--print-path",
        ], check=False)

        # RED: Expect only the path on stdout; logs go to stderr.
        # Current behavior prints a human log line on stdout as well → should fail before fix.
        stdout_lines = [l for l in res.stdout.splitlines() if l.strip()]
        self.assertEqual(len(stdout_lines), 1, f"stdout should contain only the path, got: {stdout_lines}")
        out_path = Path(stdout_lines[0])
        self.assertTrue(out_path.name == "implementation-report.json")
        self.assertIn("Implementation report", res.stderr or "", "status/log messages must be in stderr")


if __name__ == "__main__":
    unittest.main()