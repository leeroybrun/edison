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
VALIDATE = REPO_ROOT / "scripts" / "validators" / "validate"


class ValidateStdoutPurityTests(unittest.TestCase):
    def setUp(self) -> None:
        # Ephemeral root the validator CLI will treat as the project root
        self.tmp = Path(tempfile.mkdtemp(prefix="validators-stdout-purity-"))
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))

        # Minimal tree + canonical config/schema to exercise normal paths
        (self.tmp / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)

        core_src = REPO_ROOT / ".edison" / "core"
        core_dst = self.tmp / ".edison" / "core"
        (core_dst / "lib").mkdir(parents=True, exist_ok=True)
        shutil.copytree(core_src / "lib", core_dst / "lib", dirs_exist_ok=True)
        shutil.copyfile(core_src / "defaults.yaml", core_dst / "defaults.yaml")
        (core_dst / "schemas").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(core_src / "schemas" / "validator-report.schema.json", core_dst / "schemas" / "validator-report.schema.json")

        agents_dst = self.tmp / ".agents"
        agents_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / ".agents" / "config.yml", agents_dst / "config.yml")

        self.env = os.environ.copy()
        self.env.update({
            "project_ROOT": str(self.tmp),  # used by the validate script to resolve repo root
            "PYTHONUNBUFFERED": "1",
        })

    def _run(self, *argv: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        cp = run_with_timeout([str(VALIDATE), *argv], cwd=REPO_ROOT, env=self.env, capture_output=True, text=True)
        if check and cp.returncode != 0:
            raise AssertionError(f"Command failed: {' '.join([str(VALIDATE), *argv])}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}")
        return cp

    def test_validate_stdout_only_bundle_path(self) -> None:
        """Verify validate outputs only bundle path to stdout"""
        task_id = "stdout-purity-missing"
        # Create an empty round directory so the CLI reaches the summary emission path
        (self.tmp / ".project" / "qa" / "validation-evidence" / task_id / "round-1").mkdir(parents=True, exist_ok=True)
        # No reports present → validator should still emit only the summary path on stdout
        out = self._run("--task", task_id)
        # Expect exactly one non-empty line with the path to bundle-approved.json
        stdout_lines = [l for l in (out.stdout or "").splitlines() if l.strip()]
        self.assertEqual(len(stdout_lines), 1, f"stdout must contain only the bundle summary path, got: {stdout_lines}")
        path = Path(stdout_lines[0])
        self.assertTrue(path.name.endswith("bundle-approved.json"), f"stdout should be the bundle summary path, got: {path}")
        # Ensure the file actually exists and is JSON
        self.assertTrue(path.exists(), f"bundle summary not created at {path}")
        json.loads(path.read_text())
        # No diagnostic phrases on stdout
        self.assertNotIn("missing report", out.stdout.lower())
        self.assertNotIn("❌", out.stdout)

    def test_validate_diagnostics_to_stderr(self) -> None:
        """Verify all diagnostic messages go to stderr"""
        task_id = "stderr-diagnostics"
        # Prepare a round directory with no reports to intentionally trigger missing report diagnostics
        (self.tmp / ".project" / "qa" / "validation-evidence" / task_id / "round-1").mkdir(parents=True, exist_ok=True)
        res = self._run("--task", task_id)
        self.assertNotEqual(res.returncode, 0, "validation should fail when required reports are missing")
        # Diagnostics should be in stderr, including the recognizable 'missing report' phrase
        self.assertIn("missing report", (res.stderr or "").lower(), f"stderr should contain diagnostics. stderr=\n{res.stderr}")
        # stdout should remain clean (single path line)
        self.assertEqual(len([l for l in (res.stdout or '').splitlines() if l.strip()]), 1)

    def test_validate_stdout_machine_parseable(self) -> None:
        """Verify stdout is always machine-parseable (single path or JSON)"""
        task_id = "machine-parseable"
        # Prepare empty round directory to exercise stdout emission logic
        (self.tmp / ".project" / "qa" / "validation-evidence" / task_id / "round-1").mkdir(parents=True, exist_ok=True)
        res = self._run("--task", task_id)
        # Try JSON first; if not JSON, treat it as a single-line path
        stdout = res.stdout.strip()
        parsed_ok = True
        try:
            _ = json.loads(stdout)
        except Exception:
            # Expect a single path line
            lines = [l for l in stdout.splitlines() if l.strip()]
            if len(lines) != 1:
                parsed_ok = False
            else:
                p = Path(lines[0])
                parsed_ok = p.exists()
        self.assertTrue(parsed_ok, f"stdout must be machine-parseable. Got:\n{stdout}\nSTDERR:\n{res.stderr}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()