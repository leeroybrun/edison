"""MCP server injection helpers for external CLI clients.

Some CLI clients (notably Codex CLI) only load MCP servers from global config,
but support per-invocation configuration overrides via CLI flags. Edison uses
these helpers to inject required MCP servers for specific agents/validators
without requiring global machine configuration.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from edison.core.mcp.config import McpServerConfig


def _toml_escape_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_array_of_strings(values: Sequence[str]) -> str:
    inner = ", ".join(_toml_escape_string(v) for v in values)
    return f"[{inner}]"


def _toml_inline_table_string_map(values: Mapping[str, str]) -> str:
    items = ", ".join(f"{k}={_toml_escape_string(v)}" for k, v in sorted(values.items()))
    return f"{{{items}}}"


def build_codex_mcp_config_overrides(
    servers: Mapping[str, McpServerConfig],
    *,
    required_servers: Sequence[str],
) -> list[str]:
    """Build `codex -c key=value` overrides to register MCP servers.

    Codex CLI stores MCP servers in `~/.codex/config.toml` under `mcp_servers.*`,
    but also supports per-invocation `-c` overrides. We use this to avoid
    mutating developer global config while still exposing required tools.

    Returns:
        A flat list of CLI args, e.g. ["-c","mcp_servers.foo.command=\"npx\"", ...].
    """
    args: list[str] = []
    for server_id in required_servers:
        if server_id not in servers:
            raise ValueError(f"Unknown MCP server '{server_id}' (not present in mcp.servers)")

        cfg = servers[server_id]
        base = f"mcp_servers.{server_id}"

        args.extend(["-c", f"{base}.command={_toml_escape_string(cfg.command)}"])
        args.extend(["-c", f"{base}.args={_toml_array_of_strings(cfg.args)}"])
        if cfg.env:
            args.extend(["-c", f"{base}.env={_toml_inline_table_string_map(cfg.env)}"])

    return args


def build_mcp_cli_overrides(
    style: str,
    servers: Mapping[str, McpServerConfig],
    *,
    required_servers: Sequence[str],
) -> list[str]:
    """Build CLI args to inject required MCP servers for a given client style."""
    style_key = str(style or "").strip().lower()
    if not required_servers:
        return []
    if style_key in {"codex", "codex_config", "codex-config"}:
        return build_codex_mcp_config_overrides(servers, required_servers=required_servers)
    raise ValueError(f"Unsupported MCP override style: {style}")


__all__ = [
    "build_codex_mcp_config_overrides",
    "build_mcp_cli_overrides",
]

