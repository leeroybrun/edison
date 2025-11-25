from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from edison.core.utils.subprocess import run_with_timeout


CORE_TEST_ROOT = Path(__file__).resolve().parents[3]  # .../.edison/core/tests
REPO_ROOT = CORE_TEST_ROOT.parents[1]  # .../example-project


def _seed_orchestrator_env(root: Path) -> None:
    """Seed isolated project root with real Edison config and packs.

    This mirrors the structure expected by ConfigManager and CompositionEngine
    so that orchestrator artifacts are generated from real defaults + project
    overlays instead of synthetic test-only data.
    """
    # Core config (defaults + modular config dir when present)
    core_src = REPO_ROOT / ".edison" / "core"
    core_dst = root / ".edison" / "core"
    core_dst.mkdir(parents=True, exist_ok=True)

    defaults_src = core_src / "defaults.yaml"
    if defaults_src.exists():
        shutil.copy(defaults_src, core_dst / "defaults.yaml")

    core_config_src = core_src / "config"
    if core_config_src.exists():
        shutil.copytree(core_config_src, core_dst / "config", dirs_exist_ok=True)

    validators_src = core_src / "validators"
    if validators_src.exists():
        shutil.copytree(validators_src, core_dst / "validators", dirs_exist_ok=True)

    # Packs tree (real packs, used for agents/guidelines metadata)
    packs_src = REPO_ROOT / ".edison" / "packs"
    packs_dst = root / ".edison" / "packs"
    if packs_src.exists():
        packs_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(packs_src, packs_dst, dirs_exist_ok=True)

    # Project-level config and delegation overlay
    agents_dst = root / ".agents"
    agents_dst.mkdir(parents=True, exist_ok=True)

    config_src = REPO_ROOT / ".agents" / "config.yml"
    if config_src.exists():
        shutil.copy(config_src, agents_dst / "config.yml")

    # Canonical delegation overlay YAML under .agents/config/delegation.yml
    delegation_yaml_src = REPO_ROOT / ".agents" / "config" / "delegation.yml"
    if delegation_yaml_src.exists():
        delegation_cfg_dir = agents_dst / "config"
        delegation_cfg_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(delegation_yaml_src, delegation_cfg_dir / "delegation.yml")


@pytest.fixture
def orchestrator_env(isolated_project_env: Path) -> Path:
    """Isolated project root pre-seeded for orchestrator composition tests."""
    root = isolated_project_env
    _seed_orchestrator_env(root)
    return root


def _run_compose_orchestrator(project_root: Path) -> tuple[int, str, str]:
    """Invoke the real compose CLI with --orchestrator under an isolated root."""
    script = REPO_ROOT / ".edison" / "core" / "scripts" / "prompts" / "compose"
    assert script.exists(), f"compose script missing at {script}"

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)

    proc = run_with_timeout(
        [str(Path(os.environ.get("PYTHON", "python3"))), str(script), "--orchestrator"],
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
    assert "validator-codex-global" in validators or "validator-claude-global" in validators


@pytest.mark.integration
def test_cli_writes_validators_into_generated_dir(orchestrator_env: Path) -> None:
    """
    Validator composition via compose CLI should write canonical outputs into
    .agents/_generated/validators/ in addition to the cache directory.
    """
    root = orchestrator_env

    script = REPO_ROOT / ".edison" / "core" / "scripts" / "prompts" / "compose"
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    proc = run_with_timeout(
        [str(Path(os.environ.get("PYTHON", "python3"))), str(script), "--validator", "all"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, f"compose --validator all failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

    generated_dir = root / ".agents" / "_generated" / "validators"
    assert generated_dir.is_dir(), "Expected .agents/_generated/validators directory to be created"

    # Core defaults define three global validators; all should be present.
    for name in ("codex-global", "claude-global", "gemini-global"):
        out_file = generated_dir / f"{name}.md"
        assert out_file.is_file(), f"Missing generated validator prompt: {out_file}"
