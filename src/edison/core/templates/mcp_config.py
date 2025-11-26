"""MCP configuration helpers shared by CLI commands.

This module centralizes creation and persistence of `.mcp.json` entries
for the edison-zen MCP server. Configuration is loaded from YAML sources
(`edison.data.config.zen.yaml` plus project overlays) with no hardcoded
values, and JSON output formatting comes from the CLI config section of
`defaults.yaml`/project overrides.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from edison.data import read_yaml
from edison.core.file_io import utils as file_utils
from edison.core.paths.project import get_project_config_dir


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


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge dictionaries without mutating inputs."""

    result = dict(base)
    for key, value in (override or {}).items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}


def _load_json_format(project_root: Path) -> Dict[str, Any]:
    """Load JSON formatting preferences from defaults + project overrides."""

    defaults = read_yaml("config", "defaults.yaml") or {}
    cli_defaults = (defaults.get("cli") or {}).get("json", {})
    json_io_cfg = defaults.get("json_io") or {}
    merged = _deep_merge(json_io_cfg, cli_defaults)

    project_config_dir = get_project_config_dir(project_root)
    project_cli_cfg = _load_yaml_file(project_config_dir / "config" / "cli.yml")
    if isinstance(project_cli_cfg, dict):
        merged = _deep_merge(merged, (project_cli_cfg.get("cli") or {}).get("json", {}))

    return {
        "indent": merged.get("indent", 2),
        "sort_keys": merged.get("sort_keys", True),
        "ensure_ascii": merged.get("ensure_ascii", False),
    }


def _load_zen_config(project_root: Path) -> Dict[str, Any]:
    """Load zen configuration with project overlays."""

    config = read_yaml("config", "zen.yaml") or {}
    project_config_dir = get_project_config_dir(project_root)
    overlay = project_config_dir / "config" / "zen.yml"
    config = _deep_merge(config, _load_yaml_file(overlay))
    return config


def _resolve_run_script_path(project_root: Path) -> Path:
    candidates = [
        project_root / ".edison" / "scripts" / "zen" / "run-server.sh",
        project_root / "scripts" / "zen" / "run-server.sh",
        Path(__file__).resolve().parents[4] / "scripts" / "zen" / "run-server.sh",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_edison_zen_config(project_root: Path, use_script: bool = False) -> McpServerConfig:
    """Build the edison-zen MCP server configuration for a project."""

    zen_cfg = _load_zen_config(project_root)
    mcp_cfg = (zen_cfg.get("zen") or {}).get("mcp") or {}

    required = ["server_id", "command", "args", "env", "config_file"]
    missing = [key for key in required if key not in mcp_cfg]
    if missing:
        raise ValueError(f"Missing zen.mcp config keys: {', '.join(missing)}")

    env_cfg = mcp_cfg.get("env") or {}
    resolved_env = {k: str(v).replace("{PROJECT_ROOT}", str(project_root.resolve())) for k, v in env_cfg.items()}

    if use_script:
        command = str(_resolve_run_script_path(project_root))
        args: list[str] = []
    else:
        command = str(mcp_cfg.get("command"))
        args = list(mcp_cfg.get("args", []))

    return McpServerConfig(command=command, args=args, env=resolved_env)


def configure_mcp_json(
    project_root: Path,
    *,
    config_file: str | Path | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
    use_shell_script: bool = False,
) -> dict[str, Any]:
    """Add or update edison-zen server entry in `.mcp.json`.

    Returns the resulting configuration dictionary with metadata under
    ``_meta`` (path, added flag). Does not write when ``dry_run`` is True.
    """

    project_root = Path(project_root).expanduser().resolve()

    zen_cfg = _load_zen_config(project_root)
    mcp_cfg = (zen_cfg.get("zen") or {}).get("mcp") or {}
    if config_file is None:
        config_file = mcp_cfg.get("config_file", ".mcp.json")

    target_path = Path(config_file)
    if not target_path.is_absolute():
        target_path = project_root / target_path

    config = McpConfig.load(target_path)
    server_id = mcp_cfg.get("server_id", "edison-zen")
    server_cfg = get_edison_zen_config(project_root, use_script=use_shell_script)

    added = False
    try:
        added = config.add_server(server_id, server_cfg, overwrite=overwrite)
    except ValueError:
        # Existing entry when overwrite is False
        added = False

    result = config.to_dict()
    result["_meta"] = {"path": str(target_path), "added": added}

    if dry_run:
        return result

    json_fmt = _load_json_format(project_root)
    config.save(target_path, json_format=json_fmt)
    return result
