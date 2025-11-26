
import json
import pytest
from pathlib import Path
from edison.core.templates.mcp_config import McpConfig, McpServerConfig, configure_mcp_json
import edison.core.templates.mcp_config as mcp_config_module

def test_debug_import_path():
    print(f"\nDEBUG: Imported mcp_config from: {mcp_config_module.__file__}")
    print(f"DEBUG: dir(configure_mcp_json): {dir(configure_mcp_json)}")
    import inspect
    print(f"DEBUG: sig: {inspect.signature(configure_mcp_json)}")

def test_mcp_config_save_roundtrip(tmp_path):
    """Verify that McpConfig saves correctly and can be loaded back."""
    config_path = tmp_path / ".mcp.json"
    
    # Create a config
    server_config = McpServerConfig(
        command="edison",
        args=["zen", "start-server"],
        env={"ZEN_WORKING_DIR": "/tmp"}
    )
    config = McpConfig(servers={"edison-zen": server_config})
    
    # Save it
    config.save(config_path)
    
    # Verify file exists
    assert config_path.exists()
    
    # Verify content structure
    with open(config_path, "r") as f:
        data = json.load(f)
    
    assert "mcpServers" in data
    assert "edison-zen" in data["mcpServers"]
    assert data["mcpServers"]["edison-zen"]["command"] == "edison"
    
    # Verify strict formatting (indent=2, sort_keys=True)
    # We read as text to check formatting
    content = config_path.read_text(encoding="utf-8")
    assert '  "mcpServers": {' in content
    assert '"edison-zen": {' in content
    
    # Verify Load
    loaded = McpConfig.load(config_path)
    assert "edison-zen" in loaded.servers
    assert loaded.servers["edison-zen"].command == "edison"

def test_configure_mcp_json_integration(tmp_path):
    """Verify the high-level configure function."""
    project_root = tmp_path
    result = configure_mcp_json(project_root, use_shell_script=False)
    
    config_path = project_root / ".mcp.json"
    assert config_path.exists()
    assert result is not None
    assert "edison-zen" in result["mcpServers"]
