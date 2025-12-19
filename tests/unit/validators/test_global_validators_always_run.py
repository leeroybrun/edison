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
from tests.helpers.paths import get_repo_root


REPO_ROOT = get_repo_root()
SCRIPTS_DIR = REPO_ROOT / "scripts"


class TestGlobalValidatorsAlwaysRun(unittest.TestCase):
    def setUp(self) -> None:
        # Ephemeral root for CLI scripts via project_ROOT override
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-globals-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

        # Minimal structure required by scripts
        (self.temp_root / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)

        # Mirror Edison data config into the ephemeral root so ConfigManager
        # and validator scripts operate against real defaults/config.
        data_src = REPO_ROOT / "src" / "edison" / "data"
        data_dst = self.temp_root / "src" / "edison" / "data"

        # Copy config directory
        if (data_src / "config").exists():
            shutil.copytree(data_src / "config", data_dst / "config", dirs_exist_ok=True)

        # Copy schemas directory
        if (data_src / "schemas").exists():
            shutil.copytree(data_src / "schemas", data_dst / "schemas", dirs_exist_ok=True)

        # Common env for subprocesses
        self.env = os.environ.copy()
        self.env.update({
            "AGENTS_PROJECT_ROOT": str(self.temp_root),
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
        """Verify all global validators have always_run: true in config (repo canonical)."""
        cfg_path = REPO_ROOT / "src" / "edison" / "data" / "config" / "validators.yaml"
        cfg = yaml.safe_load(cfg_path.read_text())
        validators_cfg = (cfg.get("validation", {}) or {}).get("validators", {}) or {}
        self.assertTrue(validators_cfg, "Config must define validation.validators")
        globals_cfg = {vid: v for vid, v in validators_cfg.items() if str(vid).startswith("global-")}
        self.assertTrue(globals_cfg, "Config must define at least one global-* validator")
        offenders = [
            vid for vid, v in globals_cfg.items()
            if not (isinstance(v, dict) and v.get("always_run", False))
        ]
        self.assertEqual(offenders, [], f"Global validators missing always_run: true → {offenders}")

    @unittest.skipUnless(
        (SCRIPTS_DIR / "validators" / "run-wave").exists(),
        "run-wave script not implemented yet"
    )
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
        self.assertIn("global-codex", seen)
        self.assertIn("global-claude", seen)

    @unittest.skipUnless(
        (SCRIPTS_DIR / "validators" / "run-wave").exists(),
        "run-wave script not implemented yet"
    )
    def test_non_global_validators_respect_triggers(self) -> None:
        """Specialized validators like 'react' do not run when no triggers match; globals still run."""
        task_id = "gv-trigger-behavior"
        (self.temp_root / ".project" / "qa" / "validation-evidence" / task_id / "round-1").mkdir(parents=True, exist_ok=True)

        cp = self._run([str(SCRIPTS_DIR / "validators" / "run-wave"), task_id, "--json"], check=True)
        summary = json.loads(cp.stdout or "{}")
        waves = summary.get("waves") or []
        all_ids = [v.get("id") for w in waves for v in (w.get("validators") or [])]

        # Global validators must be present
        self.assertIn("global-codex", all_ids)
        self.assertIn("global-claude", all_ids)
        # React (specialized) should not be scheduled without triggers
        self.assertNotIn("react", all_ids)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
