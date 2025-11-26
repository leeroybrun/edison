"""MCP configuration helpers shared by CLI commands.

This module centralizes creation and persistence of `.mcp.json` entries for
all Edison-managed MCP servers. Configuration is fully YAML-driven
(`edison.data.config.mcp.yml` + pack overlays + project overrides) with no
hardcoded values, and JSON output formatting comes from the CLI config
section of `defaults.yaml`/project overrides.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Sequence

import yaml

from edison.data import read_yaml
from edison.core.file_io import utils as file_utils
from edison.core.paths.project import get_project_config_dir
from edison.core.utils.merge import deep_merge


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

        data = file_utils.read_json_safe(path)

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

        file_utils.write_json_safe(
            path,
            self.to_dict(),
            indent=int(fmt.get("indent", 2)),
            sort_keys=bool(fmt.get("sort_keys", True)),
            ensure_ascii=bool(fmt.get("ensure_ascii", False)),
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    data = file_utils.read_yaml_safe(path, default={})
    return data if isinstance(data, dict) else {}


def _load_json_format(project_root: Path) -> Dict[str, Any]:
    """Load JSON formatting preferences from defaults + project overrides."""

    defaults = read_yaml("config", "defaults.yaml") or {}
    cli_defaults = (defaults.get("cli") or {}).get("json", {})
    json_io_cfg = defaults.get("json_io") or {}
    merged = deep_merge(json_io_cfg, cli_defaults)

    project_config_dir = get_project_config_dir(project_root)
    project_cli_cfg = _load_yaml_file(project_config_dir / "config" / "cli.yml")
    if isinstance(project_cli_cfg, dict):
        merged = deep_merge(merged, (project_cli_cfg.get("cli") or {}).get("json", {}))

    return {
        "indent": merged.get("indent", 2),
        "sort_keys": merged.get("sort_keys", True),
        "ensure_ascii": merged.get("ensure_ascii", False),
    }


def _iter_pack_overlays(project_root: Path, packs: Sequence[str] | None) -> Iterable[Path]:
    """Yield pack-level mcp.yml files for the requested packs (if any)."""

    pack_root = get_project_config_dir(project_root, create=False) / "packs"
    if not pack_root.exists():
        return []

    allowed = set(packs) if packs else None
    overlays: list[Path] = []

    for pack_dir in sorted(p for p in pack_root.iterdir() if p.is_dir()):
        if allowed and pack_dir.name not in allowed:
            continue
        for fname in ("mcp.yml", "mcp.yaml"):
            candidate = pack_dir / "config" / fname
            if candidate.exists():
                overlays.append(candidate)
    return overlays


def _load_mcp_config(project_root: Path, packs: Sequence[str] | None = None) -> Dict[str, Any]:
    """Load MCP configuration from base + pack overlays + project overrides."""

    merged = (read_yaml("config", "mcp.yml") or {}).get("mcp") or {}

    for overlay_path in _iter_pack_overlays(project_root, packs):
        overlay = (_load_yaml_file(overlay_path).get("mcp") or {})
        merged = deep_merge(merged, overlay)

    project_config_dir = get_project_config_dir(project_root)
    for fname in ("mcp.yml", "mcp.yaml"):
        overlay_path = project_config_dir / "config" / fname
        if overlay_path.exists():
            overlay = (_load_yaml_file(overlay_path).get("mcp") or {})
            merged = deep_merge(merged, overlay)

    return merged


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

        resolved_env = {
            k: str(v).replace("{PROJECT_ROOT}", str(project_root))
            for k, v in env_raw.items()
        }

        servers[server_id] = McpServerConfig(
            command=str(cmd_source.get("command")),
            args=[str(a).replace("{PROJECT_ROOT}", str(project_root)) for a in args_raw],
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
