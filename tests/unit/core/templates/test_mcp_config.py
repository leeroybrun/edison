import json
from pathlib import Path

from edison.core.mcp.config import (
    McpServerConfig,
    build_mcp_servers,
    configure_mcp_json,
)


def test_build_mcp_servers_merges_overrides(tmp_path: Path) -> None:
    """Base + pack + project overlays should merge into final catalog."""

    project_root = tmp_path

    pack_cfg_dir = project_root / ".edison" / "packs" / "custom" / "config"
    pack_cfg_dir.mkdir(parents=True)
    (pack_cfg_dir / "mcp.yaml").write_text(
        """
mcp:
  servers:
    context7:
      env:
        CTX_TOKEN: "pack"
    custom-server:
      command: "custom"
      args: ["serve"]
      env:
        LEVEL: "pack"
""",
        encoding="utf-8",
    )

    project_cfg_dir = project_root / ".edison" / "config"
    project_cfg_dir.mkdir(parents=True, exist_ok=True)
    (project_cfg_dir / "mcp.yaml").write_text(
        """
mcp:
  config_file: ".mcp.json"
  servers:
    context7:
      env:
        CTX_TOKEN: "project"
        REGION: "local"
""",
        encoding="utf-8",
    )

    config_path, servers, setup = build_mcp_servers(project_root)

    assert config_path.name == ".mcp.json"
    assert "edison-zen" in servers
    assert "context7" in servers
    assert "custom-server" in servers
    assert isinstance(servers["context7"], McpServerConfig)
    assert servers["context7"].env["CTX_TOKEN"] == "project"
    assert servers["context7"].env["REGION"] == "local"
    assert servers["custom-server"].env["LEVEL"] == "pack"
    assert setup.get("edison-zen") is not None


def test_configure_mcp_json_preserves_user_servers(tmp_path: Path) -> None:
    """configure_mcp_json updates managed servers and leaves user servers untouched."""

    project_root = tmp_path
    existing = {
        "mcpServers": {
            "user-defined": {"command": "custom", "args": [], "env": {"X": "1"}},
            "edison-zen": {"command": "legacy", "args": [], "env": {}},
        }
    }
    (project_root / ".mcp.json").write_text(json.dumps(existing))

    result = configure_mcp_json(project_root=project_root, overwrite=True, dry_run=False)

    data = json.loads((project_root / ".mcp.json").read_text())
    assert "user-defined" in data["mcpServers"]
    assert data["mcpServers"]["user-defined"]["command"] == "custom"
    assert data["mcpServers"]["edison-zen"]["command"] != "legacy"
    assert "context7" in data["mcpServers"]
    assert result["_meta"]["path"] == str(project_root / ".mcp.json")


def test_configure_mcp_json_dry_run_returns_structure(tmp_path: Path) -> None:
    """Dry-run returns merged config without touching disk."""

    project_root = tmp_path

    result = configure_mcp_json(project_root=project_root, dry_run=True)

    assert not (project_root / ".mcp.json").exists()
    assert "mcpServers" in result
    assert "edison-zen" in result["mcpServers"]
    assert "context7" in result["mcpServers"]
