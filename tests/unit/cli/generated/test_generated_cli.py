"""CLI tests for reading/listing .edison/_generated artifacts (no mocks)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _base_env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    env.setdefault("PYTHONPATH", os.getcwd() + "/src")
    return env


def run_edison(args: list[str], *, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "edison.cli._dispatcher", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def test_generated_list_and_read_markdown_without_extension(tmp_path: Path) -> None:
    project = tmp_path / "project"
    gen = project / ".edison" / "_generated" / "start"
    gen.mkdir(parents=True)
    (gen / "START_NEW_SESSION.md").write_text("# START_NEW_SESSION\n\nHello\n", encoding="utf-8")

    env = _base_env(project)

    proc_list = run_edison(
        ["list", "--type", "start", "--format", "detail", "--json", "--repo-root", str(project)],
        env=env,
        cwd=project,
    )
    assert proc_list.returncode == 0, f"Command failed:\n{proc_list.stdout}\n{proc_list.stderr}"
    payload = json.loads(proc_list.stdout)
    files = payload.get("files")
    assert isinstance(files, list)
    detail = next((f for f in files if isinstance(f, dict) and f.get("name") == "START_NEW_SESSION.md"), None)
    assert isinstance(detail, dict)
    assert detail.get("relpath") == "start/START_NEW_SESSION.md"
    assert isinstance(detail.get("summary"), str) and detail["summary"].strip()

    proc_read = run_edison(
        ["read", "START_NEW_SESSION", "--type", "start", "--repo-root", str(project)],
        env=env,
        cwd=project,
    )
    assert proc_read.returncode == 0, f"Command failed:\n{proc_read.stdout}\n{proc_read.stderr}"
    assert "# START_NEW_SESSION" in proc_read.stdout


def test_generated_read_rejects_path_traversal(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".edison" / "_generated").mkdir(parents=True)

    proc = run_edison(
        ["read", "../secrets", "--type", "start", "--repo-root", str(project)],
        env=_base_env(project),
        cwd=project,
    )
    assert proc.returncode != 0


def test_generated_read_supports_nested_type(tmp_path: Path) -> None:
    project = tmp_path / "project"
    nested = project / ".edison" / "_generated" / "guidelines" / "agents"
    nested.mkdir(parents=True)
    (nested / "OUTPUT_FORMAT.md").write_text("# OUTPUT_FORMAT\n\nFormat rules\n", encoding="utf-8")

    proc = run_edison(
        ["read", "OUTPUT_FORMAT", "--type", "guidelines/agents", "--repo-root", str(project)],
        env=_base_env(project),
        cwd=project,
    )
    assert proc.returncode == 0, f"Command failed:\n{proc.stdout}\n{proc.stderr}"
    assert "# OUTPUT_FORMAT" in proc.stdout


def test_generated_list_rejects_type_traversal(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".edison" / "_generated").mkdir(parents=True)

    proc = run_edison(
        ["list", "--type", "../secrets", "--repo-root", str(project)],
        env=_base_env(project),
        cwd=project,
    )
    assert proc.returncode != 0


def test_generated_read_can_extract_a_section(tmp_path: Path) -> None:
    project = tmp_path / "project"
    path = project / ".edison" / "_generated" / "guidelines" / "shared" / "GIT_WORKFLOW.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# GIT_WORKFLOW\n\n"
        "<!-- section: agent -->\n"
        "Agent rules.\n"
        "<!-- /section: agent -->\n"
        "\n"
        "<!-- section: orchestrator -->\n"
        "Orchestrator rules.\n"
        "<!-- /section: orchestrator -->\n",
        encoding="utf-8",
    )

    proc = run_edison(
        [
            "read",
            "GIT_WORKFLOW",
            "--type",
            "guidelines/shared",
            "--section",
            "agent",
            "--repo-root",
            str(project),
        ],
        env=_base_env(project),
        cwd=project,
    )
    assert proc.returncode == 0, f"Command failed:\n{proc.stdout}\n{proc.stderr}"
    assert "Agent rules." in proc.stdout
    assert "Orchestrator rules." not in proc.stdout


def test_generated_read_section_missing_fails(tmp_path: Path) -> None:
    project = tmp_path / "project"
    path = project / ".edison" / "_generated" / "guidelines" / "shared" / "GIT_WORKFLOW.md"
    path.parent.mkdir(parents=True)
    path.write_text("# GIT_WORKFLOW\n\nNo sections.\n", encoding="utf-8")

    proc = run_edison(
        [
            "read",
            "GIT_WORKFLOW",
            "--type",
            "guidelines/shared",
            "--section",
            "missing",
            "--repo-root",
            str(project),
        ],
        env=_base_env(project),
        cwd=project,
    )
    assert proc.returncode != 0
