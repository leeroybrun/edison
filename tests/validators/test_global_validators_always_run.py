from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

import yaml
from edison.core.utils.subprocess import run_with_timeout


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


class GlobalValidatorsAlwaysRunTests(unittest.TestCase):
    def setUp(self) -> None:
        # Ephemeral root for CLI scripts via project_ROOT override
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-globals-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

        # Minimal structure required by scripts
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

        # Common env for subprocesses
        self.env = os.environ.copy()
        self.env.update({
            "project_ROOT": str(self.temp_root),
            "PYTHONUNBUFFERED": "1",
        })

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        cp = run_with_timeout(args, cwd=REPO_ROOT, env=self.env, capture_output=True, text=True)
        if check and cp.returncode != 0:
            raise AssertionError(
                f"Command failed: {' '.join(args)}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}"
            )
        return cp

    def test_global_validators_have_always_run_true(self) -> None:
        """Verify all global validators have alwaysRun: true in config (repo canonical)."""
        cfg_path = REPO_ROOT / ".edison" / "core" / "defaults.yaml"
        cfg = yaml.safe_load(cfg_path.read_text())
        globals_cfg = (cfg.get("validation", {}) or {}).get("roster", {}).get("global", [])
        self.assertTrue(globals_cfg, "Config must define validators.global")
        offenders = [v["id"] for v in globals_cfg if not v.get("alwaysRun", False)]
        self.assertEqual(offenders, [], f"Global validators missing alwaysRun: true → {offenders}")

    def test_global_validators_run_on_all_tasks(self) -> None:
        """Global validators appear in run-wave roster even with no triggers/files."""
        task_id = "gv-all-tasks"
        # Create empty round to avoid early exits in helper readers
        (self.temp_root / ".project" / "qa" / "validation-evidence" / task_id / "round-1").mkdir(parents=True, exist_ok=True)

        cp = self._run([str(SCRIPTS_DIR / "validators" / "run-wave"), task_id, "--json"], check=True)
        summary = json.loads(cp.stdout or "{}")
        waves = summary.get("waves") or []
        self.assertTrue(waves, "run-wave must produce at least one wave")
        seen = {v.get("id") for w in waves for v in (w.get("validators") or [])}
        self.assertIn("codex-global", seen)
        self.assertIn("claude-global", seen)

    def test_non_global_validators_respect_triggers(self) -> None:
        """Specialized validators like 'react' do not run when no triggers match; globals still run."""
        task_id = "gv-trigger-behavior"
        (self.temp_root / ".project" / "qa" / "validation-evidence" / task_id / "round-1").mkdir(parents=True, exist_ok=True)

        cp = self._run([str(SCRIPTS_DIR / "validators" / "run-wave"), task_id, "--json"], check=True)
        summary = json.loads(cp.stdout or "{}")
        waves = summary.get("waves") or []
        all_ids = [v.get("id") for w in waves for v in (w.get("validators") or [])]

        # Global validators must be present
        self.assertIn("codex-global", all_ids)
        self.assertIn("claude-global", all_ids)
        # React (specialized) should not be scheduled without triggers
        self.assertNotIn("react", all_ids)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()