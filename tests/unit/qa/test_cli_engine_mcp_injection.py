from __future__ import annotations

from pathlib import Path

from edison.core.qa.engines.base import EngineConfig
from edison.core.qa.engines.cli import CLIEngine
from edison.core.registries.validators import ValidatorMetadata
from tests.helpers.io_utils import write_yaml


def test_cli_engine_injects_mcp_overrides_for_codex_validator(
    isolated_project_env: Path,
) -> None:
    repo_root = isolated_project_env

    # Ensure the e2e-web pack is active so the MCP server catalog includes playwright.
    write_yaml(
        repo_root / ".edison" / "config" / "packs.yaml",
        {"packs": {"active": ["python", "e2e-web"]}},
    )

    engine_cfg = EngineConfig.from_dict(
        "codex-cli",
        {
            "type": "cli",
            "command": "codex",
            "pre_flags": ["--sandbox", "workspace-write"],
            "subcommand": "exec",
            "output_flags": ["--json"],
            "prompt_mode": "stdin",
            "stdin_prompt_arg": "-",
            "mcp_override_style": "codex_config",
        },
    )
    engine = CLIEngine(engine_cfg, project_root=repo_root)

    validator = ValidatorMetadata(
        id="browser-e2e",
        name="Browser E2E",
        engine="codex-cli",
        wave="comprehensive",
        prompt="",
        timeout=1,
        mcp_servers=["playwright"],
    )

    cmd = engine._build_command(validator, repo_root, prompt_args=["-"])

    assert "-c" in cmd
    assert any(v.startswith("mcp_servers.playwright.command=") for v in cmd)
    assert any(v.startswith("mcp_servers.playwright.args=") for v in cmd)

