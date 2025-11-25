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


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / "scripts"


class ValidatorConfigAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        # Ephemeral root used by scripts via project_ROOT override
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-validator-tests-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

        # Minimal project structure rooted at temp_root
        (self.temp_root / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)

        # Mirror Edison core essentials into the ephemeral root so ConfigManager
        # and validator scripts operate against real defaults/config.
        core_src = REPO_ROOT / ".edison" / "core"
        core_dst = self.temp_root / ".edison" / "core"
        (core_dst / "lib").mkdir(parents=True, exist_ok=True)
        shutil.copytree(core_src / "lib", core_dst / "lib", dirs_exist_ok=True)
        shutil.copyfile(core_src / "defaults.yaml", core_dst / "defaults.yaml")

        (core_dst / "schemas").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(core_src / "schemas" / "validator-report.schema.json", core_dst / "schemas" / "validator-report.schema.json")

        agents_dst = self.temp_root / ".agents"
        agents_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / ".agents" / "config.yml", agents_dst / "config.yml")

        # Base env used for CLI calls
        self.env = os.environ.copy()
        self.env.update({
            "project_ROOT": str(self.temp_root),
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
        cp = run_with_timeout(args, cwd=REPO_ROOT, env=self.env, capture_output=True, text=True)
        if check and cp.returncode != 0:
            raise AssertionError(f"Command failed: {' '.join(args)}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}")
        return cp

    def test_schema_tracking_requires_completedAt(self) -> None:
        # Assert canonical schema declares tracking.completedAt as required
        schema = json.loads((REPO_ROOT / ".edison" / "core" / "schemas" / "validator-report.schema.json").read_text())
        tracking_props = schema.get("properties", {}).get("tracking", {})
        required = set(tracking_props.get("required", []))
        # RED: currently missing 'completedAt' in required list
        self.assertIn("completedAt", required, "Schema must require tracking.completedAt")

    def test_prisma_id_required_not_database(self) -> None:
        task_id = "ws4-id-rename"
        round_n = 1
        # Provide all except the specialized 'prisma'; include a misnamed legacy 'database' file to ensure it's not accepted
        self._write_report(task_id, round_n, "codex-global", "codex", "approve")
        self._write_report(task_id, round_n, "claude-global", "claude", "approve")
        self._write_report(task_id, round_n, "security", "codex", "approve")
        self._write_report(task_id, round_n, "performance", "codex", "approve")
        # misnamed specialized report
        ev_dir = self.temp_root / ".project" / "qa" / "validation-evidence" / task_id / f"round-{round_n}"
        ev_dir.mkdir(parents=True, exist_ok=True)
        (ev_dir / "validator-database-report.json").write_text("{}")
        # testing specialized present
        self._write_report(task_id, round_n, "testing", "codex", "approve")

        cp = self._run([str(SCRIPTS_DIR / "validators" / "validate"), "--task", task_id], check=False)
        # Expect failure because validator-prisma report is missing
        self.assertNotEqual(cp.returncode, 0, "Validation must fail when 'prisma' report is missing")
        combined_out = (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        self.assertIn("validator-prisma-report.json", combined_out)

    def test_run_wave_uses_configured_bundle_summary_path(self) -> None:
        task_id = "ws4-bundle-path"
        round_n = 1
        # Update project config to set custom bundle summary filename in unified config
        cfg_path = self.temp_root / ".agents" / "config.yml"
        base = (REPO_ROOT / ".agents" / "config.yml").read_text()
        extra = "\nvalidation:\n  artifactPaths:\n    bundleSummaryFile: bundle-summary.json\n"
        cfg_path.write_text(base + extra)

        # Prepare fully approved reports and create ONLY the custom-named bundle summary
        for vid, model in [
            ("codex-global", "codex"), ("claude-global", "claude"),
            ("security", "codex"), ("performance", "codex"),
            ("prisma", "codex"), ("testing", "codex")
        ]:
            self._write_report(task_id, round_n, vid, model, "approve")

        ev_dir = self.temp_root / ".project" / "qa" / "validation-evidence" / task_id / f"round-{round_n}"
        ev_dir.mkdir(parents=True, exist_ok=True)
        (ev_dir / "bundle-summary.json").write_text(json.dumps({"taskId": task_id, "round": round_n, "approved": True, "validators": []}))
        # Do NOT create bundle-approved.json so a hardcoded path will miss it

        cp = self._run([str(SCRIPTS_DIR / "validators" / "run-wave"), "--task", task_id, "--json"], check=False)
        # RED: Should read bundleSummaryFile from config and include it in JSON output
        self.assertEqual(cp.returncode, 0, "run-wave should not fail when bundle summary exists at configured path")
        summary = json.loads(cp.stdout or "{}")
        self.assertTrue(summary.get("bundleApproved") in {True, False}, "run-wave must emit bundleApproved field")
        # Expect it to load the custom summary file into bundleSummary
        self.assertTrue(bool(summary.get("bundleSummary")), "run-wave must load bundle summary JSON from configured path when present")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
