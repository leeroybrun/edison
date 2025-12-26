from __future__ import annotations

from pathlib import Path
import os

from edison.core.utils.subprocess import run_with_timeout


def test_compose_all_ensures_project_gitignore_entries(isolated_project_env: Path) -> None:
    root = isolated_project_env

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    result = run_with_timeout(
        ["uv", "run", "edison", "compose", "all"],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, (
        f"compose failed with exit code {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    gitignore = root / ".gitignore"
    assert gitignore.exists(), ".gitignore should be created/updated by compose"

    content = gitignore.read_text(encoding="utf-8")
    assert ".edison/_generated/" in content
    assert ".project/sessions/" in content

