from __future__ import annotations

import json
from pathlib import Path

import sys

import pytest
import jsonschema

# Repository root for test fixtures
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

from edison.core.composition import CompositionEngine  # type: ignore  # noqa: E402


class TestOrchestratorManifest:
    def _write_defaults(self, core_dir: Path) -> None:
        """Write a minimal defaults.yaml for validation/delegation config."""
        try:
            import yaml  # type: ignore
        except Exception as err:  # pragma: no cover - surfaced by core tests
            pytest.skip(f"PyYAML not available: {err}")

        defaults = {
            "validation": {
                "roster": {
                    "global": [
                        {"name": "codex-global", "model": "codex", "blocking": False},
                    ],
                    "critical": [],
                    "specialized": [],
                }
            },
            "delegation": {
                "filePatterns": {},
                "taskTypes": {},
            },
        }
        (core_dir / "defaults.yaml").write_text(
            yaml.safe_dump(defaults), encoding="utf-8"
        )

    def _write_core_guidelines(self, core_dir: Path) -> None:
        guidelines_dir = core_dir / "guidelines"
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        (guidelines_dir / "SESSION_WORKFLOW.md").write_text(
            "# Session Workflow", encoding="utf-8"
        )
        (guidelines_dir / "DELEGATION.md").write_text(
            "# Delegation", encoding="utf-8"
        )
        (guidelines_dir / "TDD.md").write_text("# TDD", encoding="utf-8")

    def test_compose_orchestrator_manifest_creates_both_files(self, tmp_path: Path) -> None:
        """Orchestrator manifest generation creates Markdown and JSON views."""
        repo_root = tmp_path
        core_dir = repo_root / ".edison" / "core"
        core_dir.mkdir(parents=True, exist_ok=True)

        self._write_defaults(core_dir)
        self._write_core_guidelines(core_dir)

        config = {
            "project": {"name": "test-project"},
            "packs": {"active": []},
            "validation": {
                "roster": {
                    "global": [
                        {"name": "codex-global", "model": "codex", "blocking": False},
                    ],
                    "critical": [],
                    "specialized": [],
                }
            },
            "delegation": {
                "filePatterns": {},
                "taskTypes": {},
            },
        }

        engine = CompositionEngine(config, repo_root=repo_root)
        output_dir = repo_root / ".agents" / "_generated"

        result = engine.compose_orchestrator_manifest(output_dir)

        # Files created
        assert result["markdown"].exists()
        assert result["json"].exists()

        # Markdown content sanity
        md_content = result["markdown"].read_text(encoding="utf-8")
        assert "Orchestrator Guide" in md_content
        assert "📋 Mandatory Preloads" in md_content
        assert "🔍 Available Validators" in md_content
        # Delegation section should be present even with minimal config
        assert "Delegation Configuration" in md_content
        assert "🔁 Workflow Loop" in md_content
        assert "scripts/session next" in md_content

        # JSON content sanity
        json_data = json.loads(result["json"].read_text(encoding="utf-8"))
        assert json_data["version"] == "2.0.0"
        assert "generated" in json_data
        assert "validators" in json_data
        assert "agents" in json_data
        assert "guidelines" in json_data
        assert "workflowLoop" in json_data
        assert "delegation" in json_data

    def test_orchestrator_manifest_includes_pack_agents(self, tmp_path: Path) -> None:
        """Orchestrator manifest discovers specialized agents from active packs."""
        repo_root = tmp_path
        core_dir = repo_root / ".edison" / "core"
        packs_dir = repo_root / ".edison" / "packs"
        core_dir.mkdir(parents=True, exist_ok=True)
        packs_dir.mkdir(parents=True, exist_ok=True)

        self._write_defaults(core_dir)
        self._write_core_guidelines(core_dir)

        # Create a minimal pack with an agent
        react_pack_agents = packs_dir / "react" / "agents"
        react_pack_agents.mkdir(parents=True, exist_ok=True)
        (react_pack_agents / "component-builder-nextjs.md").write_text(
            "# Component Builder", encoding="utf-8"
        )

        config = {
            "project": {"name": "test-project"},
            "packs": {"active": ["react"]},
            "validation": {
                "roster": {
                    "global": [],
                    "critical": [],
                    "specialized": [],
                }
            },
            "delegation": {
                "filePatterns": {},
                "taskTypes": {},
            },
        }

        engine = CompositionEngine(config, repo_root=repo_root)
        output_dir = repo_root / ".agents" / "_generated"

        result = engine.compose_orchestrator_manifest(output_dir)

        json_data = json.loads(result["json"].read_text(encoding="utf-8"))
        assert "component-builder-nextjs" in json_data["agents"]["specialized"]

    def test_orchestrator_manifest_uses_agent_registry_for_roster(self, tmp_path: Path) -> None:
        """Orchestrator manifest agent roster is derived from AgentRegistry."""
        repo_root = tmp_path
        core_dir = repo_root / ".edison" / "core"
        packs_dir = repo_root / ".edison" / "packs"
        project_dir = repo_root / ".agents"
        core_dir.mkdir(parents=True, exist_ok=True)
        packs_dir.mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)

        self._write_defaults(core_dir)
        self._write_core_guidelines(core_dir)

        # Core agent template
        core_agents_dir = core_dir / "agents"
        core_agents_dir.mkdir(parents=True, exist_ok=True)
        (core_agents_dir / "feature-implementer-core.md").write_text(
            "\n".join(
                [
                    "# Agent: {{AGENT_NAME}}",
                    "",
                    "## Role",
                    "Feature implementer.",
                    "",
                    "## Tools",
                    "{{TOOLS}}",
                    "",
                    "## Guidelines",
                    "{{GUIDELINES}}",
                    "",
                    "## Workflows",
                    "- Core workflow",
                ]
            ),
            encoding="utf-8",
        )

        # Pack overlay
        pack_agents_dir = packs_dir / "react" / "agents"
        pack_agents_dir.mkdir(parents=True, exist_ok=True)
        (pack_agents_dir / "feature-implementer.md").write_text(
            "# feature-implementer overlay for react\n\n## Tools\n- react tool\n",
            encoding="utf-8",
        )

        # Project overlay
        project_agents_dir = project_dir / "agents"
        project_agents_dir.mkdir(parents=True, exist_ok=True)
        (project_agents_dir / "feature-implementer.md").write_text(
            "# Project feature implementer\n\n## Tools\n- project tool\n",
            encoding="utf-8",
        )

        config = {
            "project": {"name": "test-project"},
            "packs": {"active": ["react"]},
            "validation": {
                "roster": {
                    "global": [],
                    "critical": [],
                    "specialized": [],
                }
            },
            "delegation": {
                "filePatterns": {},
                "taskTypes": {},
            },
        }

        engine = CompositionEngine(config, repo_root=repo_root)
        output_dir = repo_root / ".agents" / "_generated"
        result = engine.compose_orchestrator_manifest(output_dir)

        json_data = json.loads(result["json"].read_text(encoding="utf-8"))
        agents = json_data["agents"]

        assert agents["generic"] == ["feature-implementer"]
        assert "feature-implementer" in agents["specialized"]
        assert "feature-implementer" in agents["project"]

    def test_orchestrator_manifest_includes_delegation_from_config(self, tmp_path: Path) -> None:
        """Delegation section is populated from core + project config."""
        repo_root = tmp_path
        core_dir = repo_root / ".edison" / "core"
        project_dir = repo_root / ".agents"
        core_dir.mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)

        self._write_defaults(core_dir)
        self._write_core_guidelines(core_dir)

        # Minimal core delegation config (matches core schema shape)
        core_delegation = {
            "filePatternRules": {
                "**/route.ts": {
                    "preferredModel": "codex",
                    "subAgentType": "api-builder",
                    "delegation": "required",
                }
            },
            "taskTypeRules": {
                "full-stack-feature": {
                    "preferredModel": "multi",
                    "preferredModels": ["gemini", "codex"],
                    "subAgentType": "feature-implementer",
                    "delegation": "partial",
                }
            },
            "subAgentDefaults": {
                "api-builder": {"defaultModel": "codex"},
            },
            "orchestratorGuidance": {
                "alwaysDelegateToSubAgent": True,
                "neverImplementDirectly": True,
            },
            "zenMcpIntegration": {
                "enabled": True,
                "availableModels": {"codex": {}, "gemini": {}},
            },
        }
        (core_dir / "delegation").mkdir(parents=True, exist_ok=True)
        (core_dir / "delegation" / "config.json").write_text(
            json.dumps(core_delegation), encoding="utf-8"
        )

        # Project overlay: priority chains and role mapping
        project_delegation = {
            "priority": {
                "implementers": ["feature-implementer"],
                "validators": ["validator-codex-global"],
            }
        }
        (project_dir / "delegation").mkdir(parents=True, exist_ok=True)
        (project_dir / "delegation" / "config.json").write_text(
            json.dumps(project_delegation), encoding="utf-8"
        )

        config = {
            "project": {"name": "test-project"},
            "packs": {"active": []},
            "validation": {
                "roster": {
                    "global": [],
                    "critical": [],
                    "specialized": [],
                }
            },
            "delegation": {
                "roleMapping": {
                    "feature-implementer": "project-feature-implementer",
                    "validator-codex-global": "project-validator-codex-global",
                }
            },
        }

        engine = CompositionEngine(config, repo_root=repo_root)
        output_dir = repo_root / ".agents" / "_generated"
        result = engine.compose_orchestrator_manifest(output_dir)

        json_data = json.loads(result["json"].read_text(encoding="utf-8"))
        delegation = json_data["delegation"]

        # Priority chains from project config
        assert delegation["priority"]["implementers"] == ["feature-implementer"]
        assert delegation["priority"]["validators"] == ["validator-codex-global"]

        # Role mapping from merged Edison config
        assert delegation["roleMapping"]["feature-implementer"] == "project-feature-implementer"
        assert (
            delegation["roleMapping"]["validator-codex-global"]
            == "project-validator-codex-global"
        )

        # Rules and defaults from core delegation config
        patterns = {rule["pattern"] for rule in delegation["filePatternRules"]}
        assert "**/route.ts" in patterns
        assert "full-stack-feature" in delegation["taskTypeRules"]
        assert delegation["subAgentDefaults"]["api-builder"]["defaultModel"] == "codex"

    def test_orchestrator_manifest_handles_missing_delegation_gracefully(
        self, tmp_path: Path
    ) -> None:
        """Manifest still includes a well-formed delegation section when configs are absent."""
        repo_root = tmp_path
        core_dir = repo_root / ".edison" / "core"
        core_dir.mkdir(parents=True, exist_ok=True)

        self._write_defaults(core_dir)
        self._write_core_guidelines(core_dir)

        config = {
            "project": {"name": "test-project"},
            "packs": {"active": []},
            "validation": {"roster": {"global": [], "critical": [], "specialized": []}},
        }

        engine = CompositionEngine(config, repo_root=repo_root)
        output_dir = repo_root / ".agents" / "_generated"
        result = engine.compose_orchestrator_manifest(output_dir)

        json_data = json.loads(result["json"].read_text(encoding="utf-8"))
        delegation = json_data["delegation"]

        assert "priority" in delegation
        assert "roleMapping" in delegation
        assert "filePatternRules" in delegation
        assert "taskTypeRules" in delegation
        assert "subAgentDefaults" in delegation

    def test_orchestrator_manifest_delegation_validates_schema(self, tmp_path: Path) -> None:
        """Delegation section conforms to orchestrator-manifest schema."""
        repo_root = tmp_path
        core_dir = repo_root / ".edison" / "core"
        project_dir = repo_root / ".agents"
        schemas_dir = core_dir / "schemas"
        core_dir.mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)
        schemas_dir.mkdir(parents=True, exist_ok=True)

        self._write_defaults(core_dir)
        self._write_core_guidelines(core_dir)

        # Use a minimal but valid delegation config to exercise schema
        delegation_cfg = {
            "filePatternRules": {},
            "taskTypeRules": {},
            "subAgentDefaults": {},
            "orchestratorGuidance": {
                "alwaysDelegateToSubAgent": True,
                "neverImplementDirectly": True,
            },
            "zenMcpIntegration": {"enabled": True, "availableModels": {}},
        }
        (core_dir / "delegation").mkdir(parents=True, exist_ok=True)
        (core_dir / "delegation" / "config.json").write_text(
            json.dumps(delegation_cfg), encoding="utf-8"
        )

        # Copy orchestrator-manifest schema into test repo root
        repo_schema = CORE_ROOT / "schemas" / "orchestrator-manifest.schema.json"  # type: ignore[operator]
        assert repo_schema.exists(), "orchestrator-manifest.schema.json missing in core schemas"
        (schemas_dir / "orchestrator-manifest.schema.json").write_text(
            repo_schema.read_text(encoding="utf-8"), encoding="utf-8"
        )

        config = {
            "project": {"name": "test-project"},
            "packs": {"active": []},
            "validation": {"roster": {"global": [], "critical": [], "specialized": []}},
        }

        engine = CompositionEngine(config, repo_root=repo_root)
        output_dir = repo_root / ".agents" / "_generated"
        result = engine.compose_orchestrator_manifest(output_dir)

        json_data = json.loads(result["json"].read_text(encoding="utf-8"))
        schema = json.loads(
            (schemas_dir / "orchestrator-manifest.schema.json").read_text(encoding="utf-8")
        )

        # Should not raise
        jsonschema.validate(instance=json_data, schema=schema)
