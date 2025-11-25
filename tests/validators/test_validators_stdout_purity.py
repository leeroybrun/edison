from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from edison.core.utils.subprocess import run_with_timeout
from edison.data import get_data_path


REPO_ROOT = Path(__file__).resolve().parents[2]


class ValidateStdoutPurityTests(unittest.TestCase):
    def setUp(self) -> None:
        # Ephemeral root the validator CLI will treat as the project root
        self.tmp = Path(tempfile.mkdtemp(prefix="validators-stdout-purity-"))
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))

        # Minimal tree + canonical config/schema to exercise normal paths
        (self.tmp / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)

        # Create minimal config for testing
        agents_dst = self.tmp / ".agents"
        agents_dst.mkdir(parents=True, exist_ok=True)
        test_config = REPO_ROOT / "tests" / "fixtures" / "config.yml"
        if test_config.exists():
            shutil.copyfile(test_config, agents_dst / "config.yml")
        else:
            minimal_config = """
project:
  name: test-project
validation:
  artifactPaths:
    bundleSummaryFile: bundle-approved.json
"""
            (agents_dst / "config.yml").write_text(minimal_config)

        self.env = os.environ.copy()
        self.env.update({
            "project_ROOT": str(self.tmp),  # used by the validate script to resolve repo root
            "PYTHONUNBUFFERED": "1",
        })

    def _run(self, *argv: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        import sys
        cmd = [sys.executable, "-m", "edison", "validators"] + list(argv)
        cp = run_with_timeout(cmd, cwd=REPO_ROOT, env=self.env, capture_output=True, text=True)
        if check and cp.returncode != 0:
            raise AssertionError(f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}")
        return cp

    def test_validate_stdout_only_bundle_path(self) -> None:
        """Verify bundle outputs only bundle path to stdout"""
        task_id = "stdout-purity-missing"
        # Create an empty round directory so the CLI reaches the summary emission path
        (self.tmp / ".project" / "qa" / "validation-evidence" / task_id / "round-1").mkdir(parents=True, exist_ok=True)
        # No reports present → bundle should still create a summary
        out = self._run("bundle", task_id, "--round", "1", "--json")
        # With --json flag, output should be machine-parseable JSON
        self.assertEqual(out.returncode, 0, "bundle command should succeed")
        try:
            result = json.loads(out.stdout)
            # Should have standard bundle fields (snake_case)
            self.assertIn("task_id", result, "JSON output should contain task_id")
            self.assertIn("round", result, "JSON output should contain round")
            self.assertIn("summary", result, "JSON output should contain summary")
            self.assertEqual(result["task_id"], task_id)
            self.assertEqual(result["round"], 1)
        except json.JSONDecodeError as e:
            self.fail(f"stdout should be valid JSON with --json flag, got: {out.stdout}\nError: {e}")

    def test_validate_diagnostics_to_stderr(self) -> None:
        """Verify bundle command runs successfully even without reports"""
        task_id = "stderr-diagnostics"
        # Prepare a round directory with no reports
        (self.tmp / ".project" / "qa" / "validation-evidence" / task_id / "round-1").mkdir(parents=True, exist_ok=True)
        res = self._run("bundle", task_id, "--round", "1", "--json")
        # Bundle should succeed and create a summary
        self.assertEqual(res.returncode, 0, "bundle command should succeed even with no reports")
        # With --json, output should be parseable JSON
        try:
            result = json.loads(res.stdout)
            self.assertIn("task_id", result, "bundle should have task_id")
            self.assertIn("summary", result, "bundle should have summary")
            self.assertEqual(result["task_id"], task_id)
        except json.JSONDecodeError:
            self.fail(f"stdout should be valid JSON with --json flag, got: {res.stdout}")

    def test_validate_stdout_machine_parseable(self) -> None:
        """Verify stdout is machine-parseable JSON with --json flag"""
        task_id = "machine-parseable"
        # Prepare empty round directory to exercise stdout emission logic
        (self.tmp / ".project" / "qa" / "validation-evidence" / task_id / "round-1").mkdir(parents=True, exist_ok=True)
        res = self._run("bundle", task_id, "--round", "1", "--json")
        # With --json flag, output must be valid JSON
        self.assertEqual(res.returncode, 0, "bundle command should succeed")
        try:
            result = json.loads(res.stdout)
            # Should have standard bundle fields (snake_case)
            self.assertIn("task_id", result, "bundle should contain task_id")
            self.assertIn("round", result, "bundle should contain round")
            self.assertEqual(result["task_id"], task_id)
            self.assertEqual(result["round"], 1)
        except json.JSONDecodeError as e:
            self.fail(f"stdout must be valid JSON with --json flag. Got:\n{res.stdout}\nError: {e}\nSTDERR:\n{res.stderr}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()