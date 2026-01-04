from __future__ import annotations

import os
from pathlib import Path

from edison.core.utils.subprocess import run_with_timeout


class TestAgentsConstitutionGeneration:
    def test_compose_all_generates_agents_constitution(self, isolated_project_env: Path) -> None:
        root = isolated_project_env

        env = os.environ.copy()
        env["AGENTS_PROJECT_ROOT"] = str(root)

        proc = run_with_timeout(
            ["uv", "run", "edison", "compose", "all"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
        )

        assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

        out_file = root / ".edison" / "_generated" / "constitutions" / "AGENTS.md"
        assert out_file.exists(), "compose --all should emit constitutions/AGENTS.md"
