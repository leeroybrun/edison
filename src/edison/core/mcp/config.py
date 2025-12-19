"""MCP configuration helpers shared by CLI commands.

This module centralizes creation and persistence of `.mcp.json` entries for
all Edison-managed MCP servers. Configuration is fully YAML-driven using
ConfigManager's pack-aware loading (core > packs > project) with no
hardcoded values, and JSON output formatting comes from the JSONIOConfig
domain configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence

from edison.core.utils import io as file_utils


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class McpServerConfig:
    command: str
    args: list[str]
    env: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "args": list(self.args),
            "env": dict(self.env),
        }


class McpConfig:
    """In-memory representation of `.mcp.json`."""

    def __init__(self, servers: dict[str, McpServerConfig] | None = None) -> None:
        self.servers: dict[str, McpServerConfig] = servers or {}

    @classmethod
    def load(cls, path: Path) -> "McpConfig":
        """Load configuration from disk, validating expected structure."""

        if not path.exists():
            return cls()

        data = file_utils.read_json(path)

        if not isinstance(data, dict):
            raise ValueError("existing .mcp.json must be a JSON object")

        raw_servers = data.get("mcpServers", {})
        if not isinstance(raw_servers, dict):
            raise ValueError("mcpServers must be an object")

        servers: dict[str, McpServerConfig] = {}
        for server_id, raw in raw_servers.items():
            if not isinstance(raw, dict):
                raise ValueError("mcpServers entries must be objects")

            servers[server_id] = McpServerConfig(
                command=str(raw.get("command", "")),
                args=list(raw.get("args", [])),
                env={k: str(v) for k, v in (raw.get("env") or {}).items()},
            )

        return cls(servers)

    def add_server(self, server_id: str, config: McpServerConfig, *, overwrite: bool = False) -> bool:
        """Add a server config.

        Returns True if the server was newly added, False if it replaced an
        existing entry. Raises when attempting to add duplicate without
        overwrite.
        """

        if server_id in self.servers and not overwrite:
            raise ValueError(f"Server '{server_id}' already exists")

        existed = server_id in self.servers
        self.servers[server_id] = config
        return not existed

    def to_dict(self) -> dict[str, Any]:
        return {"mcpServers": {k: v.to_dict() for k, v in self.servers.items()}}

    def save(self, path: Path, json_format: dict[str, Any] | None = None) -> None:
        """Persist configuration atomically using shared file helpers."""

        fmt = {"indent": 2, "sort_keys": True, "ensure_ascii": False}
        if json_format:
            fmt.update(json_format)

        file_utils.write_json_atomic(
            path,
            self.to_dict(),
            indent=int(fmt.get("indent", 2)),
            sort_keys=bool(fmt.get("sort_keys", True)),
            ensure_ascii=bool(fmt.get("ensure_ascii", False)),
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_json_format(project_root: Path) -> Dict[str, Any]:
    """Load JSON formatting preferences from JSONIOConfig domain config."""
    from edison.core.config.domains.json_io import JSONIOConfig

    cfg = JSONIOConfig(repo_root=project_root)
    return {
        "indent": cfg.indent,
        "sort_keys": cfg.sort_keys,
        "ensure_ascii": cfg.ensure_ascii,
    }


def _load_mcp_config(project_root: Path, packs: Sequence[str] | None = None) -> Dict[str, Any]:
    """Load MCP configuration using ConfigManager's pack-aware loading.

    ConfigManager handles the full layering:
    1. Core config (bundled mcp.yaml)
    2. Pack configs (bundled + project packs)
    3. Project config (<project-config-dir>/config/mcp.yaml)

    Args:
        project_root: Project root path
        packs: Optional list of packs (ignored - ConfigManager uses packs.active)

    Returns:
        Merged MCP configuration dict
    """
    from edison.core.config import ConfigManager

    cfg_mgr = ConfigManager(repo_root=project_root)
    full_config = cfg_mgr.load_config(validate=False, include_packs=True)
    return full_config.get("mcp", {}) or {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_mcp_servers(
    project_root: Path,
    packs: Sequence[str] | None = None,
    *,
    prefer_scripts: bool = False,
) -> tuple[Path, dict[str, McpServerConfig], dict[str, Dict[str, Any]]]:
    """Build merged MCP server catalog.

    Returns:
        Tuple of (config_path, servers_dict, setup_metadata)
    """

    project_root = Path(project_root).expanduser().resolve()
    mcp_cfg = _load_mcp_config(project_root, packs=packs)

    config_file = mcp_cfg.get("config_file", ".mcp.json")
    target_path = Path(config_file)
    if not target_path.is_absolute():
        target_path = project_root / target_path

    servers: dict[str, McpServerConfig] = {}
    setup: dict[str, Dict[str, Any]] = {}

    for server_id, raw in (mcp_cfg.get("servers") or {}).items():
        if not isinstance(raw, dict):
            continue
        if "command" not in raw:
            raise ValueError(f"Missing command for MCP server '{server_id}'")

        script_cfg = raw.get("script") if prefer_scripts else None
        cmd_source = script_cfg if isinstance(script_cfg, dict) else raw

        args_raw = cmd_source.get("args") or []
        env_raw = raw.get("env") or {}

        if not isinstance(env_raw, dict):
            raise ValueError(f"env for MCP server '{server_id}' must be a mapping")

        resolved_env = {k: str(v) for k, v in env_raw.items()}

        servers[server_id] = McpServerConfig(
            command=str(cmd_source.get("command")),
            args=[str(a) for a in args_raw],
            env=resolved_env,
        )
        setup[server_id] = dict(raw.get("setup") or {})

    return target_path, servers, setup


def configure_mcp_json(
    project_root: Path,
    *,
    config_file: str | Path | None = None,
    server_ids: Sequence[str] | None = None,
    packs: Sequence[str] | None = None,
    overwrite: bool = True,
    dry_run: bool = False,
    prefer_scripts: bool = False,
) -> dict[str, Any]:
    """Write (or simulate) an updated `.mcp.json` using YAML-driven values.

    Args:
        project_root: Project root path.
        config_file: Optional override for the target .mcp.json path.
        server_ids: Limit updates to the specified server ids (default all managed).
        packs: Optional list of packs whose overrides should be applied.
        overwrite: Whether to replace existing managed entries.
        dry_run: When True, return config without writing to disk.
    """

    project_root = Path(project_root).expanduser().resolve()
    target_path, servers, _ = build_mcp_servers(project_root, packs=packs, prefer_scripts=prefer_scripts)

    if server_ids is not None:
        servers = {sid: cfg for sid, cfg in servers.items() if sid in server_ids}

    if config_file is not None:
        cfg_path = Path(config_file)
        if not cfg_path.is_absolute():
            cfg_path = project_root / cfg_path
        target_path = cfg_path

    config = McpConfig.load(target_path)

    added_count = 0
    for server_id, server_cfg in servers.items():
        is_new = config.add_server(server_id, server_cfg, overwrite=overwrite)
        if is_new:
            added_count += 1

    result = config.to_dict()
    result["_meta"] = {"path": str(target_path), "added": added_count}

    if dry_run:
        return result

    json_fmt = _load_json_format(project_root)
    config.save(target_path, json_format=json_fmt)
    return result


__all__ = [
    "McpServerConfig",
    "McpConfig",
    "build_mcp_servers",
    "configure_mcp_json",
]
