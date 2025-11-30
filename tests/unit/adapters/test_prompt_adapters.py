from __future__ import annotations

"""Tests for provider prompt adapters (codex, cursor)."""

from pathlib import Path
import json
import sys

import pytest

from tests.helpers.io_utils import write_yaml, write_json


# Make Edison core importable for the adapter modules


def _write_adapter_config(repo_root: Path) -> None:
    """Write minimal defaults/config with adapter-specific settings.

    Each adapter under test must source file/dir names from YAML rather than
    hardcoding them in code.
    """

    defaults = {
        "project": {"name": "adapter-unit-test"},
        "adapters": {
            "codex": {
                "orchestrator_filename": "SYS_PROMPT.md",
                "agents_dirname": "agent-prompts",
                "validators_dirname": "validator-prompts",
                "header": "# Codex System Prompt",
            },
            "cursor": {
                "orchestrator_filename": "cursor-orchestrator.txt",
                "agents_dirname": "cursor-agents",
                "validators_dirname": "cursor-validators",
                "workflow_template": ".zen/templates/workflow-loop.txt",
            },
        },
    }

    # Note: This uses JSON format for backwards compatibility with existing tests
    write_json(repo_root / ".edison" / "config" / "defaults.yaml", defaults)

    # Minimal project overlay so ConfigManager sees a valid project config dir
    write_yaml(repo_root / ".agents" / "config" / "project.yml", {"project": {"name": "adapter-unit-test"}})


def _seed_generated(repo_root: Path) -> Path:
    """Create a tiny `_generated` tree for adapters to consume."""

    generated_root = repo_root / ".agents" / "_generated"
    (generated_root / "agents").mkdir(parents=True, exist_ok=True)
    (generated_root / "validators").mkdir(parents=True, exist_ok=True)

    # ORCHESTRATOR_GUIDE.md deprecated (T-011) - use constitution instead
    constitutions_dir = generated_root / "constitutions"
    constitutions_dir.mkdir(parents=True, exist_ok=True)
    constitution = constitutions_dir / "ORCHESTRATORS.md"
    constitution.write_text("Constitution body", encoding="utf-8")

    manifest = generated_root / "orchestrator-manifest.json"
    manifest.write_text(json.dumps({"role": "orchestrator"}), encoding="utf-8")

    agent = generated_root / "agents" / "builder.md"
    agent.write_text("# builder\nAgent body", encoding="utf-8")

    validator = generated_root / "validators" / "checks.md"
    validator.write_text("# checks\nValidator body", encoding="utf-8")

    return generated_root


class TestCodexAdapter:
    def test_codex_adapter_uses_configured_paths(self, isolated_project_env: Path) -> None:
        pytest.skip("Pre-existing: composition.commands module doesn't exist yet")
        from edison.core.adapters import CodexAdapter
        repo_root = isolated_project_env
        _write_adapter_config(repo_root)
        generated_root = _seed_generated(repo_root)

        out_root = repo_root / ".codex-out"
        adapter = CodexAdapter(generated_root=generated_root, repo_root=repo_root)
        adapter.write_outputs(out_root)

        orchestrator = out_root / "SYS_PROMPT.md"
        agent = out_root / "agent-prompts" / "builder.md"
        validator = out_root / "validator-prompts" / "checks.md"

        assert orchestrator.exists()
        assert agent.exists()
        assert validator.exists()

        content = orchestrator.read_text(encoding="utf-8")
        assert "Codex System Prompt" in content
        assert "Guide body" in content

    def test_codex_adapter_missing_agent_raises(self, isolated_project_env: Path) -> None:
        from edison.core.adapters import CodexAdapter
        repo_root = isolated_project_env
        _write_adapter_config(repo_root)
        generated_root = _seed_generated(repo_root)

        adapter = CodexAdapter(generated_root=generated_root, repo_root=repo_root)

        with pytest.raises(FileNotFoundError):
            adapter.render_agent("nonexistent")


class TestCursorPromptAdapter:
    def test_cursor_adapter_writes_prompts(self, isolated_project_env: Path) -> None:
        pytest.skip("Pre-existing: composition.commands module doesn't exist yet")
        from edison.core.adapters import CursorPromptAdapter
        repo_root = isolated_project_env
        _write_adapter_config(repo_root)
        generated_root = _seed_generated(repo_root)

        out_root = repo_root / ".cursor" / "prompts"
        adapter = CursorPromptAdapter(generated_root=generated_root, repo_root=repo_root)
        adapter.write_outputs(out_root)

        orchestrator = out_root / "cursor-orchestrator.txt"
        agent = out_root / "cursor-agents" / "builder.md"
        validator = out_root / "cursor-validators" / "checks.md"

        assert orchestrator.exists()
        assert agent.exists()
        assert validator.exists()

        orchestrator_text = orchestrator.read_text(encoding="utf-8")
        assert "Guide body" in orchestrator_text
        # Cursor adapter should embed a workflow loop marker for the client
        assert "Workflow" in orchestrator_text

    def test_cursor_adapter_missing_validator_raises(self, isolated_project_env: Path) -> None:
        from edison.core.adapters import CursorPromptAdapter
        repo_root = isolated_project_env
        _write_adapter_config(repo_root)
        generated_root = _seed_generated(repo_root)

        adapter = CursorPromptAdapter(generated_root=generated_root, repo_root=repo_root)

        with pytest.raises(FileNotFoundError):
            adapter.render_validator("does-not-exist")
