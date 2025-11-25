from __future__ import annotations

from pathlib import Path
import os
import subprocess
from edison.core.utils.subprocess import run_with_timeout


class TestAgentCompositionE2E:
    def _write_core_agent(self, root: Path, name: str) -> Path:
        core_agents_dir = root / ".edison" / "core" / "agents"
        core_agents_dir.mkdir(parents=True, exist_ok=True)
        path = core_agents_dir / f"{name}-core.md"
        content = "\n".join(
            [
                "# Agent: {{AGENT_NAME}}",
                "",
                "## Role",
                "Core role for {{AGENT_NAME}} (packs: {{PACK_NAME}}).",
                "",
                "## Tools",
                "{{TOOLS}}",
                "",
                "## Guidelines",
                "{{GUIDELINES}}",
                "",
                "## Workflows",
                "- Core workflow step",
            ]
        )
        path.write_text(content, encoding="utf-8")
        return path

    def _write_pack_overlay(self, root: Path, pack: str, agent: str) -> Path:
        pack_agents_dir = root / ".edison" / "packs" / pack / "agents"
        pack_agents_dir.mkdir(parents=True, exist_ok=True)
        path = pack_agents_dir / f"{agent}.md"
        content = "\n".join(
            [
                f"# {agent} overlay for {pack}",
                "",
                "## Tools",
                f"- {pack} tool",
                "",
                "## Guidelines",
                f"- {pack} guideline",
            ]
        )
        path.write_text(content, encoding="utf-8")
        return path

    def _write_defaults_and_config(self, root: Path, packs: list[str]) -> None:
        """Write minimal defaults.yaml and .agents/config/packs.yml for the test project."""
        core_dir = root / ".edison" / "core"
        core_dir.mkdir(parents=True, exist_ok=True)
        defaults = "\n".join(
            [
                "project:",
                "  name: Test Project",
                "packs:",
                f"  active: [{', '.join(packs)}]",
            ]
        )
        (core_dir / "defaults.yaml").write_text(defaults, encoding="utf-8")

        # Write config in the correct modular location
        config_dir = root / ".agents" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        packs_config = "\n".join(
            [
                "packs:",
                f"  active: [{', '.join(packs)}]",
            ]
        )
        (config_dir / "packs.yml").write_text(packs_config, encoding="utf-8")

    def _assert_agent_schema(self, text: str) -> None:
        """Lightweight schema check for generated agent Markdown."""
        assert "# Agent:" in text
        assert "## Role" in text
        assert "## Tools" in text
        assert "## Guidelines" in text
        assert "## Workflows" in text

    def test_full_pipeline_multi_pack_agent(self, isolated_project_env: Path) -> None:
        """CLI composes agents end-to-end for multiple packs."""
        root = isolated_project_env
        self._write_defaults_and_config(root, packs=["react", "fastify"])
        self._write_core_agent(root, "api-builder")
        self._write_pack_overlay(root, "react", "api-builder")
        self._write_pack_overlay(root, "fastify", "api-builder")

        env = os.environ.copy()
        env["AGENTS_PROJECT_ROOT"] = str(root)

        result = run_with_timeout(
            ["uv", "run", "edison", "compose", "all", "--agents"],
            cwd=root,
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0, (
            f"compose script failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

        generated = root / ".agents" / "_generated" / "agents" / "api-builder.md"
        assert generated.exists()
        content = generated.read_text(encoding="utf-8")

        self._assert_agent_schema(content)
        # Multi-pack content should be present
        assert "react tool" in content
        assert "fastify tool" in content
        # Pack names should be visible in the composed output
        assert "react, fastify" in content or "fastify, react" in content

