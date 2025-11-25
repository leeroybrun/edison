from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from edison.core.utils.subprocess import run_with_timeout


# REPO_ROOT is the Edison repo root (not Wilson)
REPO_ROOT = Path(__file__).resolve().parents[3]  # edison/tests/integration/composition -> edison/


def _seed_orchestrator_env(root: Path) -> None:
    """Seed isolated project root with real Edison bundled data.

    This mirrors the structure expected by ConfigManager and CompositionEngine
    so that orchestrator artifacts are generated from real bundled data + synthetic
    project config.
    """
    # Copy bundled Edison data (packs, core config) from the edison package
    from edison.data import get_data_path

    bundled_core = get_data_path("")
    core_dst = root / ".edison" / "core"
    if bundled_core.exists():
        shutil.copytree(bundled_core, core_dst, dirs_exist_ok=True)

    bundled_packs = get_data_path("packs")
    packs_dst = root / ".edison" / "packs"
    if bundled_packs.exists():
        shutil.copytree(bundled_packs, packs_dst, dirs_exist_ok=True)

    # Create minimal project config with modular structure
    agents_dst = root / ".agents"
    agents_dst.mkdir(parents=True, exist_ok=True)

    config_dir = agents_dst / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create packs.yml with active packs (must merge into existing packs config)
    # Also specify that .agents is the project config dir (not .edison)
    packs_config = {
        "paths": {
            "project_config_dir": ".agents"
        },
        "packs": {
            "active": ["nextjs", "react", "prisma", "fastify"]
        }
    }
    (config_dir / "packs.yml").write_text(yaml.dump(packs_config), encoding="utf-8")

    # Create minimal delegation.yml
    delegation_config = """delegation:
  priority:
    implementers:
      - api-builder
      - feature-implementer
    validators:
      - codex-global
      - claude-global
"""
    (config_dir / "delegation.yml").write_text(delegation_config, encoding="utf-8")


@pytest.fixture
def orchestrator_env(isolated_project_env: Path) -> Path:
    """Isolated project root pre-seeded for orchestrator composition tests."""
    root = isolated_project_env
    _seed_orchestrator_env(root)
    return root


def _run_compose_orchestrator(project_root: Path) -> tuple[int, str, str]:
    """Invoke the real compose CLI with --orchestrator under an isolated root."""
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
def test_orchestrator_manifest_written_to_generated_dir(orchestrator_env: Path) -> None:
    """compose --orchestrator must write manifest + guide into .agents/_generated/."""
    root = orchestrator_env

    code, out, err = _run_compose_orchestrator(root)
    assert code == 0, f"compose --orchestrator failed\nstdout:\n{out}\nstderr:\n{err}"

    manifest_path = root / ".agents" / "_generated" / "orchestrator-manifest.json"
    guide_path = root / ".agents" / "_generated" / "ORCHESTRATOR_GUIDE.md"

    assert manifest_path.is_file(), f"Missing orchestrator manifest at {manifest_path}"
    assert guide_path.is_file(), f"Missing orchestrator guide at {guide_path}"


@pytest.mark.integration
def test_manifest_includes_active_packs_and_validators(orchestrator_env: Path) -> None:
    """Manifest JSON should expose active packs and validator roster."""
    root = orchestrator_env

    code, out, err = _run_compose_orchestrator(root)
    assert code == 0, f"compose --orchestrator failed\nstdout:\n{out}\nstderr:\n{err}"

    manifest_path = root / ".agents" / "_generated" / "orchestrator-manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Active packs
    packs = data.get("composition", {}).get("packs", [])
    assert isinstance(packs, list), "composition.packs must be a list"
    # Config for this repo enables multiple packs; ensure at least one surfaced.
    assert len(packs) >= 1, "Expected at least one active pack in manifest"

    # Validators roster (global / critical / specialized)
    validators = data.get("validators", {})
    assert isinstance(validators, dict), "validators block must be an object"
    for key in ("global", "critical", "specialized"):
        assert key in validators, f"validators['{key}'] missing from manifest"
        assert isinstance(validators[key], list), f"validators['{key}'] must be a list"

    global_ids = {v.get("id") for v in validators.get("global", []) if isinstance(v, dict)}
    # Core defaults include these three globals.
    for vid in ("codex-global", "claude-global", "gemini-global"):
        assert vid in global_ids, f"{vid} not present in manifest.validators.global"


@pytest.mark.integration
def test_manifest_includes_delegation_hints(orchestrator_env: Path) -> None:
    """Delegation block should include priority chains for implementers/validators."""
    root = orchestrator_env

    code, out, err = _run_compose_orchestrator(root)
    assert code == 0, f"compose --orchestrator failed\nstdout:\n{out}\nstderr:\n{err}"

    manifest_path = root / ".agents" / "_generated" / "orchestrator-manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    delegation = data.get("delegation") or {}
    assert isinstance(delegation, dict), "delegation block must be an object"

    priority = delegation.get("priority") or {}
    assert isinstance(priority, dict), "delegation.priority must be an object"

    implementers = priority.get("implementers") or []
    validators = priority.get("validators") or []

    assert isinstance(implementers, list), "delegation.priority.implementers must be a list"
    assert isinstance(validators, list), "delegation.priority.validators must be a list"
    # Use real project overlay (delegation/config.json) via _seed_orchestrator_env.
    assert "api-builder" in implementers or "feature-implementer" in implementers
    assert "codex-global" in validators or "claude-global" in validators


@pytest.mark.integration
def test_cli_writes_validators_into_generated_dir(orchestrator_env: Path) -> None:
    """
    Validator composition via compose CLI should write canonical outputs into
    .agents/_generated/validators/ in addition to the cache directory.
    """
    root = orchestrator_env

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    proc = run_with_timeout(
        ["uv", "run", "edison", "compose", "all", "--validators"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, f"compose --validators failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

    generated_dir = root / ".agents" / "_generated" / "validators"
    assert generated_dir.is_dir(), "Expected .agents/_generated/validators directory to be created"

    # Core defaults define three global validators; all should be present.
    for name in ("codex-global", "claude-global", "gemini-global"):
        out_file = generated_dir / f"{name}.md"
        assert out_file.is_file(), f"Missing generated validator prompt: {out_file}"
