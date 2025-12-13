from __future__ import annotations

from pathlib import Path
import os
import subprocess

from helpers.io_utils import write_text
from edison.core.utils.subprocess import run_with_timeout


class TestAgentCompositionE2E:
    def _write_pack_overlay(self, root: Path, pack: str, agent: str) -> Path:
        """Write a pack-specific agent overlay file."""
        pack_agents_dir = root / ".edison" / "packs" / pack / "agents" / "overlays"
        pack_agents_dir.mkdir(parents=True, exist_ok=True)
        path = pack_agents_dir / f"{agent}.md"
        content = "\n".join(
            [
                f"# {agent} overlay for {pack}",
                "",
                "<!-- extend: tools -->",
                f"- {pack} tool",
                "<!-- /extend -->",
            ]
        )
        write_text(path, content)
        return path

    def _write_defaults_and_config(self, root: Path, packs: list[str]) -> None:
        """Write minimal .edison/config/packs.yaml for the test project."""
        config_dir = root / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        packs_config = "\n".join(["packs:", f"  active: [{', '.join(packs)}]"])
        write_text(config_dir / "packs.yaml", packs_config)

    def _assert_agent_schema(self, text: str) -> None:
        """Lightweight schema check for generated agent Markdown."""
        assert "name: api-builder" in text
        assert "## Tools" in text

    def test_full_pipeline_multi_pack_agent(self, isolated_project_env: Path) -> None:
        """CLI composes agents end-to-end for multiple packs."""
        root = isolated_project_env
        self._write_defaults_and_config(root, packs=["react", "fastify"])
        self._write_pack_overlay(root, "react", "api-builder")
        self._write_pack_overlay(root, "fastify", "api-builder")

        env = os.environ.copy()
        env["AGENTS_PROJECT_ROOT"] = str(root)

        result = run_with_timeout(
            ["uv", "run", "edison", "compose", "all"],
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

        generated = root / ".edison" / "_generated" / "agents" / "api-builder.md"
        assert generated.exists()
        content = generated.read_text(encoding="utf-8")

        self._assert_agent_schema(content)
        # Multi-pack content should be present
        assert "react tool" in content
        assert "fastify tool" in content

