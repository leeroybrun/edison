from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.helpers.paths import get_repo_root
from tests.helpers.timeouts import SUBPROCESS_TIMEOUT


REPO_ROOT = get_repo_root()
# Note: Legacy .edison/core/scripts has been migrated to Python modules
# This test now verifies utility scripts in the root scripts/ directory
SCRIPTS_ROOT = REPO_ROOT / "scripts"
EXPECTED_SHEBANG = "#!/usr/bin/env python3"


def _python_scripts() -> list[Path]:
    """Find Python scripts that should have shebangs and exec permissions.

    Only looks for standalone executable scripts (not library modules).
    """
    scripts: list[Path] = []
    if not SCRIPTS_ROOT.exists():
        return scripts

    for path in SCRIPTS_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
            continue

        # Only check files with shebang (intended to be executable)
        try:
            first = path.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
        except Exception:
            continue
        if first.startswith("#!") and "python" in first:
            scripts.append(path)

    return sorted(scripts)


@pytest.mark.integration
def test_python_scripts_have_shebang_and_exec_bits():
    """Verify executable Python scripts have proper shebang and permissions.

    Note: After migration to Python modules, most functionality is in src/edison/core.
    This test only checks utility scripts that are still meant to be directly executable.
    """
    scripts = _python_scripts()
    if not scripts:
        pytest.skip("No executable Python scripts found (expected after migration to modules)")

    for script in scripts:
        lines = script.read_text(encoding="utf-8", errors="ignore").splitlines()
        assert lines, f"{script} is empty"
        assert lines[0].strip() == EXPECTED_SHEBANG, f"{script} missing python3 shebang"
        assert os.access(script, os.X_OK), f"{script} is not executable"


@pytest.mark.integration
def test_python_scripts_help_runs_without_permission_errors():
    """Verify executable scripts can be run without permission errors.

    Note: After migration to Python modules, most functionality is in src/edison/core.
    This test only checks utility scripts that are still meant to be directly executable.
    """
    scripts = _python_scripts()
    if not scripts:
        pytest.skip("No executable Python scripts found (expected after migration to modules)")

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(REPO_ROOT)

    for script in scripts:
        try:
            proc = subprocess.run(
                [str(script), "--help"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=SUBPROCESS_TIMEOUT / 8,
            )
        except PermissionError as err:  # pragma: no cover - exercised via assertion
            pytest.fail(f"{script} raised PermissionError: {err}")

        output = (proc.stdout + proc.stderr).lower()
        perm_codes = {13, 126}
        assert proc.returncode not in perm_codes, (
            f"{script} failed with permission-related return code {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
        assert "permission denied" not in output and "operation not permitted" not in output, (
            f"{script} output indicates permission issues\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
