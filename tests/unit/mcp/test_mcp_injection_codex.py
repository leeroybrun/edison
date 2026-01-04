from __future__ import annotations

from edison.core.mcp.injection import build_codex_mcp_config_overrides
from edison.core.mcp.config import McpServerConfig


def test_build_codex_mcp_config_overrides_emits_toml_overrides() -> None:
    servers = {
        "playwright": McpServerConfig(
            command="npx",
            args=["-y", "@playwright/mcp@latest", "--isolated"],
            env={"FOO": "bar"},
        )
    }

    args = build_codex_mcp_config_overrides(servers, required_servers=["playwright"])

    # Expect pairs of "-c", "key=value" suitable for `codex -c ...`.
    assert args.count("-c") >= 2
    assert any(v.startswith("mcp_servers.playwright.command=") for v in args)
    assert any(v.startswith("mcp_servers.playwright.args=") for v in args)
    assert any(v.startswith("mcp_servers.playwright.env=") for v in args)

