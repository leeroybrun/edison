from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_ROOT = Path(__file__).resolve().parents[2] / "scripts"
EXPECTED_SHEBANG = "#!/usr/bin/env python3"


def _python_scripts() -> list[Path]:
    scripts: list[Path] = []
    for path in SCRIPTS_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
            continue

        if path.suffix == ".py":
            scripts.append(path)
            continue

        try:
            first = path.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
        except Exception:
            continue
        if first.startswith("#!") and "python" in first:
            scripts.append(path)

    return sorted(scripts)


@pytest.mark.integration
def test_python_scripts_have_shebang_and_exec_bits():
    scripts = _python_scripts()
    assert scripts, "Expected python scripts under .edison/core/scripts"

    for script in scripts:
        lines = script.read_text(encoding="utf-8", errors="ignore").splitlines()
        assert lines, f"{script} is empty"
        assert lines[0].strip() == EXPECTED_SHEBANG, f"{script} missing python3 shebang"
        assert os.access(script, os.X_OK), f"{script} is not executable"


@pytest.mark.integration
def test_python_scripts_help_runs_without_permission_errors():
    scripts = _python_scripts()
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
                timeout=15,
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
