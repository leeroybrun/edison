from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.adapters import CursorSync


def _write_minimal_config(root: Path) -> None:
    """Write minimal defaults/config needed for ConfigManager-based adapters."""
    core_dir = root / ".edison" / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    defaults = "\n".join(
        [
            "project:",
            "  name: cursor-unit-test",
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
            "  name: cursor-unit-test",
            "packs:",
            "  active: []",
        ]
    )
    (agents_dir / "config.yml").write_text(config + "\n", encoding="utf-8")


class TestCursorAdapterCursorrules:
    def test_cursorrules_includes_guidelines_and_rules(self, isolated_project_env: Path) -> None:
        project_root = isolated_project_env

        _write_minimal_config(project_root)

        # Minimal guideline setup - create in 'shared' subdirectory to match registry path
        guidelines_dir = project_root / ".edison" / "core" / "guidelines" / "shared"
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        guideline_path = guidelines_dir / "architecture.md"
        guideline_path.write_text(
            "# Architecture\n\nCore architecture guidance.\n", encoding="utf-8"
        )

        # Minimal rules registry referencing the guideline
        rules_dir = project_root / ".edison" / "core" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        registry_path = rules_dir / "registry.yml"
        registry_path.write_text(
            "version: '1.0.0'\n"
            "rules:\n"
            "  - id: arch-1\n"
            "    title: Architecture rule\n"
            "    blocking: true\n"
            "    contexts: ['architecture']\n"
            "    source:\n"
            "      file: '.edison/core/guidelines/shared/architecture.md'\n",
            encoding="utf-8",
        )

        adapter = CursorSync(project_root=project_root)
        out_path = adapter.sync_to_cursorrules()

        assert out_path.name == ".cursorrules"
        content = out_path.read_text(encoding="utf-8")

        # Guideline content should be present
        assert "Architecture" in content
        assert "Core architecture guidance." in content

        # Rule id and title should be present
        assert "arch-1" in content
        assert "Architecture rule" in content

    def test_detect_cursor_overrides_reports_manual_changes(
        self, isolated_project_env: Path
    ) -> None:
        project_root = isolated_project_env

        _write_minimal_config(project_root)

        # Baseline guideline/rule so sync_to_cursorrules can run
        guidelines_dir = project_root / ".edison" / "core" / "guidelines"
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        (guidelines_dir / "arch.md").write_text("# Arch\n\nText.\n", encoding="utf-8")

        rules_dir = project_root / ".edison" / "core" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        (rules_dir / "registry.yml").write_text(
            "version: '1.0.0'\n"
            "rules:\n"
            "  - id: r1\n"
            "    title: R1\n"
            "    blocking: false\n"
            "    contexts: []\n",
            encoding="utf-8",
        )

        adapter = CursorSync(project_root=project_root)
        path = adapter.sync_to_cursorrules()

        # Manual edit after initial sync
        path.write_text(path.read_text(encoding="utf-8") + "\n\n# Manual tweak\nNote.\n", encoding="utf-8")

        report = adapter.detect_cursor_overrides()

        assert report["fileExists"] is True
        assert report["snapshotExists"] is True
        assert report["has_overrides"] is True
        diff_text = "\n".join(report.get("diff", []))
        assert "Manual tweak" in diff_text

    def test_merge_preserves_manual_header_on_resync(self, isolated_project_env: Path) -> None:
        project_root = isolated_project_env

        _write_minimal_config(project_root)

        # Guideline and rules
        guidelines_dir = project_root / ".edison" / "core" / "guidelines"
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        guideline_path = guidelines_dir / "architecture.md"
        guideline_path.write_text("# Architecture\n\nOriginal.\n", encoding="utf-8")

        rules_dir = project_root / ".edison" / "core" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        registry_path = rules_dir / "registry.yml"
        registry_path.write_text(
            "version: '1.0.0'\n"
            "rules:\n"
            "  - id: arch-1\n"
            "    title: Architecture rule\n"
            "    blocking: false\n"
            "    contexts: []\n",
            encoding="utf-8",
        )

        adapter = CursorSync(project_root=project_root)
        path = adapter.sync_to_cursorrules()

        # Add a manual header above the generated block
        original = path.read_text(encoding="utf-8")
        path.write_text("# Manual header\nImportant notes.\n\n" + original, encoding="utf-8")

        # Change guideline content to force a different generated section
        guideline_path.write_text("# Architecture\n\nUpdated guidance.\n", encoding="utf-8")

        path2 = adapter.sync_to_cursorrules()
        final = path2.read_text(encoding="utf-8")

        # Manual header should be preserved
        assert "# Manual header" in final
        assert "Important notes." in final

        # New guideline content should be present after resync
        assert "Updated guidance." in final


class TestCursorAdapterAgentSync:
    def test_sync_agents_copies_generated_agents(self, isolated_project_env: Path) -> None:
        project_root = isolated_project_env

        _write_minimal_config(project_root)

        # Simulate composed agents under .edison/_generated/agents
        generated_agents_dir = project_root / ".edison" / "_generated" / "agents"
        generated_agents_dir.mkdir(parents=True, exist_ok=True)
        agent_file = generated_agents_dir / "api-builder.md"
        agent_file.write_text("# Agent: api-builder\nDetails.\n", encoding="utf-8")

        adapter = CursorSync(project_root=project_root)
        copied = adapter.sync_agents_to_cursor()

        cursor_agents_dir = project_root / ".cursor" / "agents"
        target = cursor_agents_dir / "api-builder.md"

        assert target in copied
        assert target.exists()
        assert "# Agent: api-builder" in target.read_text(encoding="utf-8")

    def test_sync_agents_auto_composes_when_missing(self, isolated_project_env: Path) -> None:
        project_root = isolated_project_env

        _write_minimal_config(project_root)

        # Core agent template but no pre-generated agents
        core_agents_dir = project_root / ".edison" / "core" / "agents"
        core_agents_dir.mkdir(parents=True, exist_ok=True)
        core_template = core_agents_dir / "api-builder.md"
        core_template.write_text(
            "# Agent: api-builder\n\n{{TOOLS}}\n\n{{GUIDELINES}}\n",
            encoding="utf-8",
        )

        adapter = CursorSync(project_root=project_root)
        copied = adapter.sync_agents_to_cursor(auto_compose=True)

        # Generated agents should now exist and be synced into .cursor/agents
        generated_agent = project_root / ".edison" / "_generated" / "agents" / "api-builder.md"
        cursor_agent = project_root / ".cursor" / "agents" / "api-builder.md"

        assert generated_agent.exists()
        assert cursor_agent in copied
        assert cursor_agent.exists()
        text = cursor_agent.read_text(encoding="utf-8")
        assert "Agent: api-builder" in text


class TestCursorAdapterStructuredRules:
    def test_structured_rules_generate_mdc_by_category(self, isolated_project_env: Path) -> None:
        project_root = isolated_project_env

        _write_minimal_config(project_root)

        # Minimal rules registry with explicit categories and inline guidance bodies
        rules_dir = project_root / ".edison" / "core" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        registry_path = rules_dir / "registry.yml"
        registry_path.write_text(
            "version: '1.0.0'\n"
            "rules:\n"
            "  - id: RULE.VALIDATION.ONE\n"
            "    title: Validation One\n"
            "    category: validation\n"
            "    blocking: true\n"
            "    guidance: 'Validation rule body.'\n"
            "  - id: RULE.DELEGATION.ONE\n"
            "    title: Delegation One\n"
            "    category: delegation\n"
            "    blocking: false\n"
            "    guidance: 'Delegation rule body.'\n"
            "  - id: RULE.CONTEXT.ONE\n"
            "    title: Context One\n"
            "    category: context\n"
            "    blocking: false\n"
            "    guidance: 'Context rule body.'\n",
            encoding="utf-8",
        )

        adapter = CursorSync(project_root=project_root)
        paths = adapter.sync_structured_rules()

        rules_root = project_root / ".cursor" / "rules"
        validation_path = rules_root / "validation.mdc"
        delegation_path = rules_root / "delegation.mdc"
        context_path = rules_root / "context.mdc"

        assert validation_path in paths
        assert delegation_path in paths
        assert context_path in paths

        validation_text = validation_path.read_text(encoding="utf-8")
        delegation_text = delegation_path.read_text(encoding="utf-8")
        context_text = context_path.read_text(encoding="utf-8")

        # Each file should contain only its own rule id and category
        assert "id: RULE.VALIDATION.ONE" in validation_text
        assert "category: validation" in validation_text
        assert "Validation rule body." in validation_text
        assert "RULE.DELEGATION.ONE" not in validation_text

        assert "id: RULE.DELEGATION.ONE" in delegation_text
        assert "category: delegation" in delegation_text
        assert "Delegation rule body." in delegation_text
        assert "RULE.VALIDATION.ONE" not in delegation_text

        assert "id: RULE.CONTEXT.ONE" in context_text
        assert "category: context" in context_text
        assert "Context rule body." in context_text
