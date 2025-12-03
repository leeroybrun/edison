import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from tests.helpers.paths import get_repo_root

EDISON_ROOT = get_repo_root()

# Skip all tests in this file - utils/verify-setup CLI functionality doesn't exist yet
# The equivalent would be 'edison config validate' but it's not implemented yet
pytestmark = pytest.mark.skip(reason="Utils verify-setup CLI has not been implemented yet. Use 'edison config validate' when available.")


def run(script: str, args: list[str], env: dict, check: bool = True) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(EDISON_ROOT / "scripts" / script), *args]
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
    """Test that verify-setup passes when project structure is valid.
    
    NOTE: This test uses the correct architecture:
    - Config: .edison/config/
    - NO .edison/core/ - core content is from bundled edison.data
    """
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(tmp_path)

    # Prepare project structure (NOT .edison/core - that is legacy)
    edison_dir = tmp_path / ".edison"
    edison_dir.mkdir(parents=True, exist_ok=True)
    
    # Project-level config overrides
    config_dir = edison_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "defaults.yaml").write_text("# Project defaults override\n")

    proc = run("utils/verify-setup.py", ["--json"], env)
    payload = json.loads(proc.stdout.strip())
    assert proc.returncode == 0
    assert payload["ok"] is True
    assert payload["missing"] == []
