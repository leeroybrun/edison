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
    raise AssertionError("cannot locate repository root for zen integration tests")


def _compose_script() -> Path:
    return _repo_root() / ".edison" / "core" / "scripts" / "prompts" / "compose"


def _write_basic_project_layout(root: Path) -> None:
    # Minimal config enabling Zen and all three models
    agents_dir = root / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "config.yml").write_text(
        "\n".join(
            [
                "project:",
                "  name: test-project",
                "packs:",
                "  active: []",
                "zen:",
                "  enabled: true",
                "  roles:",
                "    - codex",
                "    - claude",
                "    - gemini",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    core_root = root / ".edison" / "core"
    core_root.mkdir(parents=True, exist_ok=True)
    defaults = core_root / "defaults.yaml"
    if not defaults.exists():
        defaults.write_text("project:\n  name: test-project\n", encoding="utf-8")

    # Guidelines used for role-specific filtering
    gdir = core_root / "guidelines"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "QUALITY.md").write_text("QUALITY-GUIDE\n", encoding="utf-8")
    (gdir / "security.md").write_text("SECURITY-GUIDE\n", encoding="utf-8")
    (gdir / "performance.md").write_text("PERFORMANCE-GUIDE\n", encoding="utf-8")
    (gdir / "architecture.md").write_text("ARCHITECTURE-GUIDE\n", encoding="utf-8")

    # Rules for review vs planning
    rdir = core_root / "rules"
    rdir.mkdir(parents=True, exist_ok=True)
    registry = """
version: 1.0.0
rules:
  - id: RULE.REVIEW.VALIDATION
    title: Validation rule for reviews
    category: validation
    blocking: true
  - id: RULE.PLANNING.DELEGATION
    title: Delegation planning rule
    category: delegation
    blocking: false
"""
    (rdir / "registry.yml").write_text(registry.strip() + "\n", encoding="utf-8")

    # Workflow loop template required by adapter
    zen_templates = root / ".zen" / "templates"
    zen_templates.mkdir(parents=True, exist_ok=True)
    (zen_templates / "workflow-loop.txt").write_text(
        "\n".join(
            [
                "## Edison Workflow Loop (CRITICAL)",
                "",
                "scripts/session next <session-id>",
                "",
                "APPLICABLE RULES (read FIRST)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_project_with_overlays_and_delegation(root: Path) -> None:
    """Project layout exercising packs, overlays, and delegation config."""
    agents_dir = root / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "guidelines").mkdir(parents=True, exist_ok=True)

    config_yml = """
project:
  name: test-project
packs:
  active:
    - fastify
    - prisma
    - vitest
zen:
  enabled: true
  roles:
    project-api-builder:
      guidelines: [api-design, validation, error-handling]
      rules: [validation, implementation]
      packs: [fastify]
    project-database-architect-prisma:
      guidelines: [database, prisma, schema-design, migrations]
      rules: [validation, implementation]
      packs: [prisma]
    project-test-engineer:
      guidelines: [testing, tdd, test-quality]
      rules: [validation]
      packs: [vitest]
delegation:
  roleMapping:
    api-builder: project-api-builder
    database-architect-prisma: project-database-architect-prisma
    test-engineer: project-test-engineer
"""
    (agents_dir / "config.yml").write_text(config_yml.strip() + "\n", encoding="utf-8")

    # Delegation config with simple priority chain
    delegation_dir = agents_dir / "delegation"
    delegation_dir.mkdir(parents=True, exist_ok=True)
    (delegation_dir / "config.json").write_text(
        """
{
  "version": "1.0.0",
  "priority": {
    "implementers": ["api-builder", "database-architect-prisma", "test-engineer"],
    "validators": []
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    core_root = root / ".edison" / "core"
    core_root.mkdir(parents=True, exist_ok=True)
    defaults = core_root / "defaults.yaml"
    if not defaults.exists():
        defaults.write_text("project:\n  name: test-project\n", encoding="utf-8")

    # Core guidelines
    gdir = core_root / "guidelines"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "api-design.md").write_text("CORE-API-DESIGN\n", encoding="utf-8")
    (gdir / "validation.md").write_text("CORE-VALIDATION\n", encoding="utf-8")
    (gdir / "error-handling.md").write_text("CORE-ERROR-HANDLING\n", encoding="utf-8")
    (gdir / "database.md").write_text("CORE-DATABASE\n", encoding="utf-8")

    # Pack guidelines
    fastify_gdir = root / ".edison" / "packs" / "fastify" / "guidelines"
    fastify_gdir.mkdir(parents=True, exist_ok=True)
    (fastify_gdir / "schema-validation.md").write_text(
        "FASTIFY-SCHEMA-VALIDATION\n", encoding="utf-8"
    )
    (fastify_gdir / "error-handling.md").write_text(
        "FASTIFY-ERROR-HANDLING\n", encoding="utf-8"
    )

    prisma_gdir = root / ".edison" / "packs" / "prisma" / "guidelines"
    prisma_gdir.mkdir(parents=True, exist_ok=True)
    (prisma_gdir / "schema-design.md").write_text(
        "prisma-SCHEMA-DESIGN\n", encoding="utf-8"
    )
    (prisma_gdir / "migrations.md").write_text("prisma-MIGRATIONS\n", encoding="utf-8")

    vitest_gdir = root / ".edison" / "packs" / "vitest" / "guidelines"
    vitest_gdir.mkdir(parents=True, exist_ok=True)
    (vitest_gdir / "test-quality.md").write_text("VITEST-TEST-QUALITY\n", encoding="utf-8")
    (vitest_gdir / "tdd-workflow.md").write_text("VITEST-TDD-WORKFLOW\n", encoding="utf-8")

    # Project overlays
    overlays_dir = agents_dir / "guidelines"
    (overlays_dir / "api-design.md").write_text(
        "PROJECT-API-DESIGN-OVERLAY\n", encoding="utf-8"
    )
    (overlays_dir / "database.md").write_text(
        "PROJECT-DATABASE-OVERLAY\n", encoding="utf-8"
    )

    # Core + pack rules for categories used in role config
    rdir = core_root / "rules"
    rdir.mkdir(parents=True, exist_ok=True)
    core_registry = """
version: 1.0.0
rules:
  - id: RULE.CORE.VALIDATION
    title: Core validation rule
    category: validation
    blocking: false
  - id: RULE.CORE.IMPLEMENTATION
    title: Core implementation rule
    category: implementation
    blocking: false
"""
    (rdir / "registry.yml").write_text(core_registry.strip() + "\n", encoding="utf-8")

    fastify_rdir = root / ".edison" / "packs" / "fastify" / "rules"
    fastify_rdir.mkdir(parents=True, exist_ok=True)
    fastify_registry = """
version: 1.0.0
rules:
  - id: RULE.FASTIFY.VALIDATION
    title: Fastify validation rule
    category: validation
    blocking: false
"""
    (fastify_rdir / "registry.yml").write_text(
        fastify_registry.strip() + "\n", encoding="utf-8"
    )

    prisma_rdir = root / ".edison" / "packs" / "prisma" / "rules"
    prisma_rdir.mkdir(parents=True, exist_ok=True)
    prisma_registry = """
version: 1.0.0
rules:
  - id: RULE.prisma.VALIDATION
    title: prisma validation rule
    category: validation
    blocking: false
"""
    (prisma_rdir / "registry.yml").write_text(
        prisma_registry.strip() + "\n", encoding="utf-8"
    )

    vitest_rdir = root / ".edison" / "packs" / "vitest" / "rules"
    vitest_rdir.mkdir(parents=True, exist_ok=True)
    vitest_registry = """
version: 1.0.0
rules:
  - id: RULE.VITEST.VALIDATION
    title: Vitest validation rule
    category: validation
    blocking: false
"""
    (vitest_rdir / "registry.yml").write_text(
        vitest_registry.strip() + "\n", encoding="utf-8"
    )

    # Workflow loop template
    zen_templates = root / ".zen" / "templates"
    zen_templates.mkdir(parents=True, exist_ok=True)
    (zen_templates / "workflow-loop.txt").write_text(
        "\n".join(
            [
                "## Edison Workflow Loop (CRITICAL)",
                "",
                "scripts/session next <session-id>",
                "",
                "APPLICABLE RULES (read FIRST)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.integration
def test_full_sync_pipeline_for_all_models(isolated_project_env: Path) -> None:
    """compose --sync-zen should generate prompts for all three models."""
    repo_root = _repo_root()
    script = _compose_script()

    _write_basic_project_layout(isolated_project_env)

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(isolated_project_env)
    env["PYTHONUNBUFFERED"] = "1"

    result = run_with_timeout(
        [str(script), "--sync-zen"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"compose --sync-zen failed: {result.stdout}\n{result.stderr}"

    prompts_dir = (
        isolated_project_env / ".zen" / "conf" / "systemprompts" / "clink" / "project"
    )
    for model in ("codex", "claude", "gemini"):
        path = prompts_dir / f"{model}.txt"
        assert path.exists(), f"missing synced prompt for {model}"
        content = path.read_text(encoding="utf-8")
        assert "Edison / Zen MCP Prompt" in content
        assert "Model: " in content
        # Workflow loop must be present and preserved
        assert "## Edison Workflow Loop" in content
        assert "APPLICABLE RULES" in content


@pytest.mark.integration
def test_multi_role_sync_and_role_specific_content(isolated_project_env: Path) -> None:
    """Syncing multiple roles should produce role-specific sections in generic prompts."""
    repo_root = _repo_root()
    script = _compose_script()

    _write_basic_project_layout(isolated_project_env)

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(isolated_project_env)
    env["PYTHONUNBUFFERED"] = "1"

    # Sync default + codereviewer + planner into codex prompt
    result = run_with_timeout(
        [
            str(script),
            "--sync-zen",
            "--sync-zen-model",
            "codex",
            "--sync-zen-role",
            "default",
            "--sync-zen-role",
            "codereviewer",
            "--sync-zen-role",
            "planner",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"compose multi-role sync failed: {result.stdout}\n{result.stderr}"

    prompts_dir = (
        isolated_project_env / ".zen" / "conf" / "systemprompts" / "clink" / "project"
    )
    codex_path = prompts_dir / "codex.txt"
    assert codex_path.exists()
    content = codex_path.read_text(encoding="utf-8")

    # We should see separate sections for codereviewer and planner with different guideline markers.
    assert "Role: codereviewer" in content
    assert "Role: planner" in content

    # Extract codereviewer section
    reviewer_start = content.index("Role: codereviewer")
    reviewer_section = content[reviewer_start:]
    reviewer_end = reviewer_section.find("Role: planner")
    if reviewer_end != -1:
        reviewer_section = reviewer_section[:reviewer_end]

    assert "QUALITY-GUIDE" in reviewer_section
    assert "ARCHITECTURE-GUIDE" not in reviewer_section

    # Planner section should emphasize architecture guideline instead
    planner_start = content.index("Role: planner")
    planner_section = content[planner_start:]
    assert "ARCHITECTURE-GUIDE" in planner_section


@pytest.mark.integration
def test_incremental_updates_preserve_workflow_loop(isolated_project_env: Path) -> None:
    """Re-running sync should update content but keep existing workflow loop section."""
    repo_root = _repo_root()
    script = _compose_script()

    _write_basic_project_layout(isolated_project_env)

    prompts_dir = (
        isolated_project_env / ".zen" / "conf" / "systemprompts" / "clink" / "project"
    )
    prompts_dir.mkdir(parents=True, exist_ok=True)
    codex_path = prompts_dir / "codex.txt"
    codex_path.write_text(
        "OLD CONTENT\n\n## Edison Workflow Loop (CRITICAL)\nOLD LOOP\n", encoding="utf-8"
    )

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(isolated_project_env)
    env["PYTHONUNBUFFERED"] = "1"

    result = run_with_timeout(
        [str(script), "--sync-zen", "--sync-zen-model", "codex", "--sync-zen-role", "default"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"compose incremental sync failed: {result.stdout}\n{result.stderr}"

    updated = codex_path.read_text(encoding="utf-8")
    assert "OLD CONTENT" not in updated
    # Existing workflow loop marker should still be present
    assert "## Edison Workflow Loop (CRITICAL)" in updated
    assert "OLD LOOP" in updated


@pytest.mark.integration
def test_project_roles_pick_up_overlays_and_packs(isolated_project_env: Path) -> None:
    """project roles should use zen.roles config, packs, and project overlays."""
    repo_root = _repo_root()
    script = _compose_script()

    _write_project_with_overlays_and_delegation(isolated_project_env)

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(isolated_project_env)
    env["PYTHONUNBUFFERED"] = "1"

    result = run_with_timeout(
        [
            str(script),
            "--sync-zen",
            "--sync-zen-model",
            "codex",
            "--sync-zen-role",
            "project-api-builder",
            "--sync-zen-role",
            "project-database-architect-prisma",
            "--sync-zen-role",
            "project-test-engineer",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0
    ), f"compose --sync-zen for project roles failed: {result.stdout}\n{result.stderr}"

    prompts_dir = (
        isolated_project_env / ".zen" / "conf" / "systemprompts" / "clink" / "project"
    )

    api_path = prompts_dir / "project-api-builder.txt"
    db_path = prompts_dir / "project-database-architect-prisma.txt"
    test_path = prompts_dir / "project-test-engineer.txt"

    assert api_path.exists()
    assert db_path.exists()
    assert test_path.exists()

    api_content = api_path.read_text(encoding="utf-8")
    # API builder should include API + validation/error guidelines and fastify pack content,
    # but not prisma-only schema guidelines.
    assert "CORE-API-DESIGN" in api_content
    assert "CORE-VALIDATION" in api_content
    assert "CORE-ERROR-HANDLING" in api_content
    assert "FASTIFY-SCHEMA-VALIDATION" in api_content
    assert "prisma-SCHEMA-DESIGN" not in api_content

    db_content = db_path.read_text(encoding="utf-8")
    # Database architect should focus on database/prisma material.
    assert "CORE-DATABASE" in db_content
    assert "prisma-SCHEMA-DESIGN" in db_content
    assert "prisma-MIGRATIONS" in db_content
    assert "FASTIFY-SCHEMA-VALIDATION" not in db_content

    test_content = test_path.read_text(encoding="utf-8")
    # Test engineer should pull Vitest/TDD guidelines.
    assert "VITEST-TEST-QUALITY" in test_content
    assert "VITEST-TDD-WORKFLOW" in test_content


@pytest.mark.integration
def test_sync_zen_from_delegation_uses_priority_and_role_mapping(
    isolated_project_env: Path,
) -> None:
    """--sync-zen-from-delegation should derive project roles from delegation config."""
    repo_root = _repo_root()
    script = _compose_script()

    _write_project_with_overlays_and_delegation(isolated_project_env)

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(isolated_project_env)
    env["PYTHONUNBUFFERED"] = "1"

    result = run_with_timeout(
        [str(script), "--sync-zen-from-delegation"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0
    ), f"compose --sync-zen-from-delegation failed: {result.stdout}\n{result.stderr}"

    prompts_dir = (
        isolated_project_env / ".zen" / "conf" / "systemprompts" / "clink" / "project"
    )

    # From delegation priority + roleMapping we expect these project roles to be synced.
    for role in ("project-api-builder", "project-database-architect-prisma", "project-test-engineer"):
        path = prompts_dir / f"{role}.txt"
        assert path.exists(), f"Missing prompt for delegated role {role}"


@pytest.mark.integration
def test_compose_zen_generates_project_api_builder_prompt_from_generated() -> None:
    """scripts/prompts/compose --zen should materialize project-api-builder prompt from _generated manifest."""
    repo_root = _repo_root()
    script = repo_root / "scripts" / "prompts" / "compose"
    assert script.exists(), "top-level compose script missing"

    result = run_with_timeout(
        [str(script), "--zen"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert (
        result.returncode == 0
    ), f"scripts/prompts/compose --zen failed: {result.stderr or result.stdout}"

    zen_prompt = (
        repo_root
        / ".zen"
        / "conf"
        / "systemprompts"
        / "clink"
        / "project"
        / "project-api-builder.txt"
    )
    assert zen_prompt.exists(), "project-api-builder Zen prompt must be generated"

    content = zen_prompt.read_text(encoding="utf-8")
    # Phase 2C requirement: Zen prompts should clearly reference the orchestrator manifest/_generated guide.
    assert (
        ".agents/_generated/orchestrator-manifest.json" in content
        or "ORCHESTRATOR_GUIDE" in content
    ), "Zen prompt should reference orchestrator manifest/_generated guide so CLI clients share the same source of truth"