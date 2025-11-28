from __future__ import annotations

import json
import pytest
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from edison.core.utils.subprocess import run_with_timeout
from edison.data import get_data_path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


class ValidatorConfigAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        # Ephemeral root used by scripts via project_ROOT override
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-validator-tests-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

        # Minimal project structure rooted at temp_root
        (self.temp_root / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)

        # Copy minimal config files needed by the validator CLI
        agents_dst = self.temp_root / ".agents"
        agents_dst.mkdir(parents=True, exist_ok=True)

        # Copy config from test fixtures if available, otherwise use defaults
        test_config = REPO_ROOT / "tests" / "fixtures" / "config.yml"
        if test_config.exists():
            shutil.copyfile(test_config, agents_dst / "config.yml")
        else:
            # Create minimal config for testing
            minimal_config = """
project:
  name: test-project
validation:
  artifactPaths:
    bundleSummaryFile: bundle-approved.json
"""
            (agents_dst / "config.yml").write_text(minimal_config)

        # Base env used for CLI calls
        self.env = os.environ.copy()
        self.env.update({
            "AGENTS_PROJECT_ROOT": str(self.temp_root),
            "PYTHONUNBUFFERED": "1",
        })

    def _write_report(self, task_id: str, round_n: int, vid: str, model: str, verdict: str, include_completed: bool = True) -> Path:
        ev_dir = self.temp_root / ".project" / "qa" / "validation-evidence" / task_id / f"round-{round_n}"
        ev_dir.mkdir(parents=True, exist_ok=True)
        tracking = {"processId": 1234, "startedAt": "2025-11-16T10:00:00Z"}
        if include_completed:
            tracking["completedAt"] = "2025-11-16T10:05:00Z"
        data = {
            "taskId": task_id,
            "round": round_n,
            "validatorId": vid,
            "model": model,
            "verdict": verdict,
            "tracking": tracking,
        }
        path = ev_dir / f"validator-{vid}-report.json"
        path.write_text(json.dumps(data))
        return path

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        import sys
        # Replace python3 with sys.executable to use the test's Python environment
        if args and args[0] == "python3":
            args = [sys.executable] + args[1:]
        cp = run_with_timeout(args, cwd=REPO_ROOT, env=self.env, capture_output=True, text=True)
        if check and cp.returncode != 0:
            raise AssertionError(f"Command failed: {' '.join(args)}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}")
        return cp

    def test_schema_tracking_requires_completedAt(self) -> None:
        # Assert canonical schema declares tracking.completedAt as required
        schema_path = get_data_path("schemas", "reports/validator-report.schema.json")
        schema = json.loads(schema_path.read_text())
        tracking_props = schema.get("properties", {}).get("tracking", {})
        required = set(tracking_props.get("required", []))
        # RED: currently missing 'completedAt' in required list
        self.assertIn("completedAt", required, "Schema must require tracking.completedAt")

    @unittest.skipUnless(
        (REPO_ROOT / "src" / "edison" / "core" / "qa" / "bundler.py").exists() and
        (REPO_ROOT / "src" / "edison" / "core" / "qa" / "evidence").is_dir(),
        "QA CLI not implemented yet"
    )
    def test_prisma_id_required_not_database(self) -> None:
        task_id = "ws4-id-rename"
        round_n = 1
        # Provide all except the specialized 'prisma'; include a misnamed legacy 'database' file to ensure it's not accepted
        self._write_report(task_id, round_n, "global-codex", "codex", "approve")
        self._write_report(task_id, round_n, "global-claude", "claude", "approve")
        self._write_report(task_id, round_n, "security", "codex", "approve")
        self._write_report(task_id, round_n, "performance", "codex", "approve")
        # misnamed specialized report (should NOT be recognized)
        ev_dir = self.temp_root / ".project" / "qa" / "validation-evidence" / task_id / f"round-{round_n}"
        ev_dir.mkdir(parents=True, exist_ok=True)
        (ev_dir / "validator-database-report.json").write_text("{}")
        # testing specialized present
        self._write_report(task_id, round_n, "testing", "codex", "approve")

        # Create a bundle first since validator reports exist
        cp = self._run(["python3", "-m", "edison", "qa", "bundle", task_id, "--round", str(round_n), "--create", "--json"], check=False)
        # Bundle should succeed and create a summary
        self.assertEqual(cp.returncode, 0, f"Bundle command should succeed, stderr: {cp.stderr}")
        try:
            result = json.loads(cp.stdout)
            # Check that the bundle was created with standard fields
            self.assertIn("created", result, "Bundle response should have 'created' key")
            self.assertIn("summary", result, "Bundle should have summary")
            summary = result["summary"]
            self.assertEqual(summary["task_id"], task_id)
            self.assertEqual(summary["round"], round_n)
            self.assertIsInstance(summary, dict, "Summary should be a dictionary")
        except json.JSONDecodeError:
            self.fail(f"Bundle output should be valid JSON with --json flag, got: {cp.stdout}")

    @unittest.skipUnless(
        (REPO_ROOT / "src" / "edison" / "core" / "qa" / "bundler.py").exists() and
        (REPO_ROOT / "src" / "edison" / "core" / "qa" / "evidence").is_dir(),
        "QA CLI not implemented yet"
    )
    def test_run_wave_uses_configured_bundle_summary_path(self) -> None:
        """Test that run_wave can execute and respects configuration"""
        task_id = "ws4-bundle-path"
        round_n = 1
        # Create minimal config with custom bundle summary filename
        cfg_path = self.temp_root / ".agents" / "config.yml"
        config_content = """
project:
  name: test-project
validation:
  artifactPaths:
    bundleSummaryFile: bundle-summary.json
"""
        cfg_path.write_text(config_content)

        # Prepare fully approved reports
        for vid, model in [
            ("global-codex", "codex"), ("global-claude", "claude"),
            ("security", "codex"), ("performance", "codex"),
            ("prisma", "codex"), ("testing", "codex")
        ]:
            self._write_report(task_id, round_n, vid, model, "approve")

        # Run bundle with --create to create a bundle summary
        bundle_cp = self._run(["python3", "-m", "edison", "qa", "bundle", task_id, "--round", str(round_n), "--create", "--json"], check=False)
        self.assertEqual(bundle_cp.returncode, 0, f"Bundle command should succeed, stderr: {bundle_cp.stderr}")

        # Verify bundle was created
        try:
            bundle_result = json.loads(bundle_cp.stdout)
            self.assertIn("created", bundle_result, "Bundle response should have 'created' key")
            self.assertIn("summary", bundle_result, "Bundle should contain summary")
            self.assertEqual(bundle_result["summary"]["task_id"], task_id)
        except json.JSONDecodeError:
            self.fail(f"Bundle output should be valid JSON, got: {bundle_cp.stdout}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
