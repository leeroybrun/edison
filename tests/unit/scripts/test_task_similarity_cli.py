from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.helpers.paths import get_repo_root

EDISON_ROOT = get_repo_root()


def _run(args: list[str], env: dict) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "edison.cli.task.similar", *args]
    src_root = str(EDISON_ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_root if not existing else f"{src_root}{os.pathsep}{existing}"
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=EDISON_ROOT,
        check=True,
    )


def test_task_similar_query_finds_existing_task(tmp_path: Path) -> None:
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    # Minimal project root
    (tmp_path / ".project" / "tasks" / "todo").mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

    repo = TaskRepository(project_root=tmp_path)
    repo.create(Task.create("300-wave1-auth-gate", "Implement auth gate", state="todo"))

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(tmp_path)
    proc = _run(["--query", "auth gate", "--json"], env)
    payload = json.loads(proc.stdout.strip())

    ids = {m["taskId"] for m in payload["matches"]}
    assert "300-wave1-auth-gate" in ids

