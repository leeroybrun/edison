from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.adapters import CursorSync
from tests.helpers.io_utils import write_yaml


def _write_minimal_config(root: Path) -> None:
    """Write minimal config needed for ConfigManager-based adapters."""
    project_data = {
        "project": {"name": "cursor-unit-test"}
    }
    write_yaml(root / ".edison" / "config" / "project.yaml", project_data)

    packs_data = {
        "packs": {"active": []}
    }
    write_yaml(root / ".edison" / "config" / "packs.yaml", packs_data)

    config_data = {
        "project": {"name": "cursor-unit-test"},
        "packs": {"active": []}
    }
    write_yaml(root / ".agents" / "config.yml", config_data)


class TestCursorAdapterCursorrules:
    def test_cursorrules_includes_guidelines_and_rules(self, isolated_project_env: Path) -> None:
        project_root = isolated_project_env

        _write_minimal_config(project_root)

        # Minimal guideline setup - create in 'shared' subdirectory to match registry path
        guidelines_dir = project_root / ".edison" / "guidelines" / "shared"
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        guideline_path = guidelines_dir / "architecture.md"
        guideline_path.write_text(
            "# Architecture\n\nCore architecture guidance.\n", encoding="utf-8"
        )

        # Minimal rules registry referencing the guideline
        registry_data = {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "arch-1",
                    "title": "Architecture rule",
                    "blocking": True,
                    "contexts": ["architecture"],
                    "source": {
                        "file": ".edison/guidelines/shared/architecture.md"
                    }
                }
            ]
        }
        write_yaml(project_root / ".edison" / "rules" / "registry.yml", registry_data)

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
        guidelines_dir = project_root / ".edison" / "guidelines"
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        (guidelines_dir / "arch.md").write_text("# Arch\n\nText.\n", encoding="utf-8")

        registry_data = {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "r1",
                    "title": "R1",
                    "blocking": False,
                    "contexts": []
                }
            ]
        }
        write_yaml(project_root / ".edison" / "rules" / "registry.yml", registry_data)

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
        guidelines_dir = project_root / ".edison" / "guidelines"
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        guideline_path = guidelines_dir / "architecture.md"
        guideline_path.write_text("# Architecture\n\nOriginal.\n", encoding="utf-8")

        registry_data = {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "arch-1",
                    "title": "Architecture rule",
                    "blocking": False,
                    "contexts": []
                }
            ]
        }
        write_yaml(project_root / ".edison" / "rules" / "registry.yml", registry_data)

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

        # Agent template but no pre-generated agents
        agents_dir = project_root / ".edison" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        agent_template = agents_dir / "api-builder.md"
        agent_template.write_text(
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
        registry_data = {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "RULE.VALIDATION.ONE",
                    "title": "Validation One",
                    "category": "validation",
                    "blocking": True,
                    "guidance": "Validation rule body."
                },
                {
                    "id": "RULE.DELEGATION.ONE",
                    "title": "Delegation One",
                    "category": "delegation",
                    "blocking": False,
                    "guidance": "Delegation rule body."
                },
                {
                    "id": "RULE.CONTEXT.ONE",
                    "title": "Context One",
                    "category": "context",
                    "blocking": False,
                    "guidance": "Context rule body."
                }
            ]
        }
        write_yaml(project_root / ".edison" / "rules" / "registry.yml", registry_data)

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
