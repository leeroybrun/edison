import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def run(script: str, args: list[str], env: dict, check: bool = True) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPTS_DIR / script), *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=env["AGENTS_PROJECT_ROOT"],
        check=check,
    )


def test_verify_setup_reports_missing(tmp_path: Path):
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(tmp_path)
    proc = run("utils/verify-setup.py", ["--json"], env, check=False)
    payload = json.loads(proc.stdout.strip())
    assert proc.returncode == 2
    assert payload["ok"] is False
    assert payload["missing"]  # at least one missing item


def test_verify_setup_passes_when_files_present(tmp_path: Path):
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(tmp_path)

    # Prepare required files
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "config.yml").write_text("project: {}\n")
    (tmp_path / ".edison" / "core").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".edison" / "core" / "defaults.yaml").write_text("cli: {}")
    include_dir = tmp_path / ".edison" / "core" / "scripts" / "include"
    include_dir.mkdir(parents=True, exist_ok=True)
    (include_dir / "render-md.sh").write_text("#!/bin/bash\necho render\n")

    proc = run("utils/verify-setup.py", ["--json"], env)
    payload = json.loads(proc.stdout.strip())
    assert proc.returncode == 0
    assert payload["ok"] is True
    assert payload["missing"] == []
