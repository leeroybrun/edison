from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess

import pytest
from edison.core.utils.subprocess import run_with_timeout


CORE_TEST_ROOT = Path(__file__).resolve().parents[3]  # .../.edison/core/tests
REPO_ROOT = CORE_TEST_ROOT.parents[1]


def _seed_orchestrator_env(root: Path) -> None:
    """Shared seeding helper for orchestrator guide tests (real config + packs)."""
    core_src = REPO_ROOT / ".edison" / "core"
    core_dst = root / ".edison" / "core"
    core_dst.mkdir(parents=True, exist_ok=True)

    defaults_src = core_src / "defaults.yaml"
    if defaults_src.exists():
        shutil.copy(defaults_src, core_dst / "defaults.yaml")

    core_config_src = core_src / "config"
    if core_config_src.exists():
        shutil.copytree(core_config_src, core_dst / "config", dirs_exist_ok=True)

    packs_src = REPO_ROOT / ".edison" / "packs"
    packs_dst = root / ".edison" / "packs"
    if packs_src.exists():
        packs_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(packs_src, packs_dst, dirs_exist_ok=True)

    agents_dst = root / ".agents"
    agents_dst.mkdir(parents=True, exist_ok=True)

    config_src = REPO_ROOT / ".agents" / "config.yml"
    if config_src.exists():
        shutil.copy(config_src, agents_dst / "config.yml")

    delegation_src = REPO_ROOT / ".agents" / "delegation" / "config.json"
    if delegation_src.exists():
        delegation_dst_dir = agents_dst / "delegation"
        delegation_dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(delegation_src, delegation_dst_dir / "config.json")


@pytest.fixture
def orchestrator_env(isolated_project_env: Path) -> Path:
    root = isolated_project_env
    _seed_orchestrator_env(root)
    return root


def _run_compose_orchestrator(project_root: Path) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)

    proc = run_with_timeout(
        ["uv", "run", "edison", "compose", "all", "--orchestrator"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.mark.integration
@pytest.mark.skip(reason="ORCHESTRATOR_GUIDE.md deprecated (T-011) - constitution system replaces it")
def test_orchestrator_guide_has_workflow_loop_section(orchestrator_env: Path) -> None:
    """DEPRECATED: ORCHESTRATOR_GUIDE.md no longer generated (T-011).

    Constitution system (constitutions/ORCHESTRATORS.md) replaces it.
    Test kept for reference but skipped.
    """
    root = orchestrator_env

    code, out, err = _run_compose_orchestrator(root)
    assert code == 0, f"compose --orchestrator failed\nstdout:\n{out}\nstderr:\n{err}"

    guide_path = root / ".agents" / "_generated" / "ORCHESTRATOR_GUIDE.md"
    assert guide_path.is_file(), f"Orchestrator guide not generated at {guide_path}"

    content = guide_path.read_text(encoding="utf-8")
    assert "Orchestrator Guide" in content
    assert "## 🔁 Workflow Loop (CRITICAL)" in content
    assert "scripts/session next <session-id>" in content
    assert "Regenerate" in content and "--orchestrator" in content


@pytest.mark.integration
@pytest.mark.skip(reason="ORCHESTRATOR_GUIDE.md deprecated (T-011) - constitution system replaces it")
def test_orchestrator_guide_summarizes_validators_and_agents(orchestrator_env: Path) -> None:
    """DEPRECATED: ORCHESTRATOR_GUIDE.md no longer generated (T-011).

    Guide functionality moved to constitution system.
    Test kept for reference but skipped.
    """
    root = orchestrator_env

    code, out, err = _run_compose_orchestrator(root)
    assert code == 0, f"compose --orchestrator failed\nstdout:\n{out}\nstderr:\n{err}"

    guide_path = root / ".agents" / "_generated" / "ORCHESTRATOR_GUIDE.md"
    content = guide_path.read_text(encoding="utf-8")

    # Validators table header + at least one known validator id
    assert "## 🔍 Available Validators" in content
    assert "Global Validators (ALWAYS run)" in content
    assert "global-codex" in content or "global-claude" in content

    # Agent sections and at least one expected agent name
    assert "## 🤖 Available Agents" in content
    assert "Generic Agents (Core framework)" in content
    assert "api-builder" in content or "feature-implementer" in content
