from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from edison.core.utils.subprocess import run_with_timeout


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if parent.name == ".edison":
            continue
        if (parent / ".git").exists():
            return parent
    raise AssertionError("cannot locate repository root for cursor integration tests")


def _compose_script() -> Path:
    return _repo_root() / ".edison" / "core" / "scripts" / "prompts" / "compose"


def _with_venv_in_path(env: dict) -> dict:
    """Ensure the Edison virtualenv (if present) is used for CLI scripts."""
    root = _repo_root()
    venv_bin = root / ".edison" / ".venv" / "bin"
    if venv_bin.exists():
        new_env = env.copy()
        new_env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
        return new_env
    return env


def _write_basic_cursor_project(root: Path) -> None:
    """Minimal Edison project layout for Cursor integration tests."""
    # Project config and defaults (packs optional for these tests)
    core_dir = root / ".edison" / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    defaults = "\n".join(
        [
            "project:",
            "  name: cursor-test-project",
            "packs:",
            "  active: []",
        ]
    )
    (core_dir / "defaults.yaml").write_text(defaults + "\n", encoding="utf-8")

    agents_dir = root / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    config = "\n".join(
        [
            "project:",
            "  name: cursor-test-project",
            "packs:",
            "  active: []",
        ]
    )
    (agents_dir / "config.yml").write_text(config + "\n", encoding="utf-8")

    # Guidelines for multi-guideline composition
    gdir = core_dir / "guidelines"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "architecture.md").write_text(
        "# Architecture\n\nARCH-GUIDE\n", encoding="utf-8"
    )
    (gdir / "quality.md").write_text("# Quality\n\nQUALITY-GUIDE\n", encoding="utf-8")

    # Simple rules registry referencing guidelines implicitly via source.file
    rdir = core_dir / "rules"
    rdir.mkdir(parents=True, exist_ok=True)
    registry = """
version: 1.0.0
rules:
  - id: RULE.ARCHITECTURE
    title: Architecture rule
    category: validation
    blocking: true
    contexts: [architecture]
    source:
      file: ".edison/core/guidelines/shared/architecture.md"
  - id: RULE.QUALITY
    title: Quality rule
    category: implementation
    blocking: false
    contexts: [quality]
    source:
      file: ".edison/core/guidelines/quality.md"
"""
    (rdir / "registry.yml").write_text(registry.strip() + "\n", encoding="utf-8")

    # Pre-composed agent artifact to sync into .cursor/agents
    generated_agents_dir = root / ".agents" / "_generated" / "agents"
    generated_agents_dir.mkdir(parents=True, exist_ok=True)
    (generated_agents_dir / "api-builder.md").write_text(
        "# Agent: api-builder\n\nCore agent for tests.\n", encoding="utf-8"
    )


def _write_cursor_project_without_generated_agents(root: Path) -> None:
    """Variant project where agents must be auto-composed."""
    _write_basic_cursor_project(root)

    # Remove pre-generated agents so auto-compose can kick in
    generated_agents_dir = root / ".agents" / "_generated" / "agents"
    if generated_agents_dir.exists():
        for path in generated_agents_dir.glob("*.md"):
            path.unlink()
    # Provide core agent template for auto-composition
    core_agents_dir = root / ".edison" / "core" / "agents"
    core_agents_dir.mkdir(parents=True, exist_ok=True)
    core_template = core_agents_dir / "api-builder-core.md"
    core_template.write_text(
        "# Agent: api-builder\n\n{{TOOLS}}\n\n{{GUIDELINES}}\n",
        encoding="utf-8",
    )


@pytest.mark.integration
def test_full_cursor_sync_pipeline(isolated_project_env: Path) -> None:
    """compose --sync-cursor should generate .cursorrules and sync agents."""
    repo_root = _repo_root()
    script = _compose_script()

    project_root = isolated_project_env
    _write_basic_cursor_project(project_root)

    env = _with_venv_in_path(os.environ.copy())
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    env["PYTHONUNBUFFERED"] = "1"

    result = run_with_timeout(
        [str(script), "--sync-cursor"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert (
        result.returncode == 0
    ), f"compose --sync-cursor failed: {result.stdout}\n{result.stderr}"

    # .cursorrules should exist and contain both guidelines and rules
    rules_path = project_root / ".cursorrules"
    assert rules_path.exists(), "missing .cursorrules after sync"
    content = rules_path.read_text(encoding="utf-8")

    assert "# Cursor Rules" in content or "# Edison Cursor Rules" in content
    # Multi-guideline composition: both guidelines must appear
    assert "ARCH-GUIDE" in content
    assert "QUALITY-GUIDE" in content
    # Rules section should include rule ids and titles
    assert "RULE.ARCHITECTURE" in content
    assert "Architecture rule" in content
    assert "RULE.QUALITY" in content
    assert "Quality rule" in content

    # Cursor agents directory should be populated from generated agents
    cursor_agents_dir = project_root / ".cursor" / "agents"
    assert cursor_agents_dir.exists()
    agent_path = cursor_agents_dir / "api-builder.md"
    assert agent_path.exists()
    agent_text = agent_path.read_text(encoding="utf-8")
    assert "Agent: api-builder" in agent_text

    # Structured rules should also be generated by default
    rules_dir = project_root / ".cursor" / "rules"
    validation_rules = rules_dir / "validation.mdc"
    implementation_rules = rules_dir / "implementation.mdc"
    assert validation_rules.exists()
    assert implementation_rules.exists()

    v_text = validation_rules.read_text(encoding="utf-8")
    i_text = implementation_rules.read_text(encoding="utf-8")
    assert "RULE.ARCHITECTURE" in v_text
    assert "RULE.QUALITY" not in v_text
    assert "RULE.QUALITY" in i_text
    assert "RULE.ARCHITECTURE" not in i_text


@pytest.mark.integration
def test_override_detection_and_preservation(isolated_project_env: Path) -> None:
    """Manual edits to .cursorrules are detected and preserved on resync."""
    repo_root = _repo_root()
    script = _compose_script()

    project_root = isolated_project_env
    _write_basic_cursor_project(project_root)

    env = _with_venv_in_path(os.environ.copy())
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    env["PYTHONUNBUFFERED"] = "1"

    # Initial sync to create baseline .cursorrules and snapshot
    first = run_with_timeout(
        [str(script), "--sync-cursor"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0, f"initial --sync-cursor failed: {first.stdout}\n{first.stderr}"

    rules_path = project_root / ".cursorrules"
    original = rules_path.read_text(encoding="utf-8")

    # Apply manual edit (override) to .cursorrules
    rules_path.write_text(
        "# Manual override header\nKeep this section.\n\n" + original,
        encoding="utf-8",
    )

    # Detect overrides via CLI
    detect = run_with_timeout(
        [str(script), "--detect-cursor-overrides"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert (
        detect.returncode == 0
    ), f"--detect-cursor-overrides failed: {detect.stdout}\n{detect.stderr}"
    assert "Manual overrides detected" in detect.stdout
    assert "Manual override header" in detect.stdout

    # Change a guideline so regenerated content differs
    arch_path = project_root / ".edison" / "core" / "guidelines" / "architecture.md"
    arch_path.write_text("# Architecture\n\nARCH-GUIDE-UPDATED\n", encoding="utf-8")

    # Resync; manual header should be preserved while generated content updates
    second = run_with_timeout(
        [str(script), "--sync-cursor"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert second.returncode == 0, f"second --sync-cursor failed: {second.stdout}\n{second.stderr}"

    updated = rules_path.read_text(encoding="utf-8")
    assert "Manual override header" in updated
    assert "Keep this section." in updated
    assert "ARCH-GUIDE-UPDATED" in updated


@pytest.mark.integration
def test_sync_cursor_rules_structured_only(isolated_project_env: Path) -> None:
    """--sync-cursor-rules --cursor-format structured should only write .mdc files."""
    repo_root = _repo_root()
    script = _compose_script()

    project_root = isolated_project_env
    _write_basic_cursor_project(project_root)

    env = _with_venv_in_path(os.environ.copy())
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    env["PYTHONUNBUFFERED"] = "1"

    result = run_with_timeout(
        [str(script), "--sync-cursor-rules", "--cursor-format", "structured"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert (
        result.returncode == 0
    ), f"compose --sync-cursor-rules --cursor-format structured failed: {result.stdout}\n{result.stderr}"

    # .cursorrules should not be created in structured-only mode
    cursorrules_path = project_root / ".cursorrules"
    assert not cursorrules_path.exists()

    rules_dir = project_root / ".cursor" / "rules"
    validation_rules = rules_dir / "validation.mdc"
    implementation_rules = rules_dir / "implementation.mdc"
    assert validation_rules.exists()
    assert implementation_rules.exists()


@pytest.mark.integration
def test_cursor_format_simple_generates_only_cursorrules(isolated_project_env: Path) -> None:
    """--cursor-format simple should not generate .cursor/rules/*.mdc."""
    repo_root = _repo_root()
    script = _compose_script()

    project_root = isolated_project_env
    _write_basic_cursor_project(project_root)

    env = _with_venv_in_path(os.environ.copy())
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    env["PYTHONUNBUFFERED"] = "1"

    result = run_with_timeout(
        [str(script), "--sync-cursor", "--cursor-format", "simple"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert (
        result.returncode == 0
    ), f"compose --sync-cursor --cursor-format simple failed: {result.stdout}\n{result.stderr}"

    rules_path = project_root / ".cursorrules"
    assert rules_path.exists()

    rules_dir = project_root / ".cursor" / "rules"
    assert not rules_dir.exists() or not any(rules_dir.glob("*.mdc"))


@pytest.mark.integration
def test_cursor_agent_auto_compose_via_cli(isolated_project_env: Path) -> None:
    """--sync-cursor-agents --auto-compose should generate and sync agents."""
    repo_root = _repo_root()
    script = _compose_script()

    project_root = isolated_project_env
    _write_cursor_project_without_generated_agents(project_root)

    env = _with_venv_in_path(os.environ.copy())
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    env["PYTHONUNBUFFERED"] = "1"

    result = run_with_timeout(
        [str(script), "--sync-cursor-agents", "--auto-compose"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert (
        result.returncode == 0
    ), f"compose --sync-cursor-agents --auto-compose failed: {result.stdout}\n{result.stderr}"

    # Agents should have been auto-composed and synced
    generated_agent = project_root / ".agents" / "_generated" / "agents" / "api-builder.md"
    cursor_agent = project_root / ".cursor" / "agents" / "api-builder.md"
    assert generated_agent.exists()
    assert cursor_agent.exists()
    assert "Agent: api-builder" in cursor_agent.read_text(encoding="utf-8")

    # CLI should log the auto-composition
    assert "Auto-composed" in result.stdout