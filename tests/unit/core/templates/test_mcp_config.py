import json
import pytest
from pathlib import Path
from unittest.mock import patch
from edison.core.templates.mcp_config import (
    McpServerConfig,
    McpConfig,
    get_edison_zen_config,
    configure_mcp_json
)

class TestMcpServerConfig:
    def test_creation(self):
        config = McpServerConfig(
            command="test-cmd",
            args=["arg1", "arg2"],
            env={"KEY": "VALUE"}
        )
        assert config.command == "test-cmd"
        assert config.args == ["arg1", "arg2"]
        assert config.env == {"KEY": "VALUE"}

    def test_to_dict(self):
        config = McpServerConfig(
            command="test-cmd",
            args=["arg1"],
            env={}
        )
        assert config.to_dict() == {
            "command": "test-cmd",
            "args": ["arg1"],
            "env": {}
        }

class TestMcpConfig:
    def test_load_missing_file(self, tmp_path):
        path = tmp_path / ".mcp.json"
        config = McpConfig.load(path)
        assert config.to_dict() == {"mcpServers": {}}

    def test_load_existing_file(self, tmp_path):
        path = tmp_path / ".mcp.json"
        data = {
            "mcpServers": {
                "existing": {"command": "echo", "args": [], "env": {}}
            }
        }
        path.write_text(json.dumps(data))
        
        config = McpConfig.load(path)
        assert "existing" in config.servers
        assert config.servers["existing"].command == "echo"

    def test_add_server(self):
        config = McpConfig()
        server_config = McpServerConfig("cmd", [], {})
        config.add_server("test-server", server_config)
        
        assert "test-server" in config.servers
        assert config.servers["test-server"] == server_config

    def test_add_server_no_overwrite(self):
        config = McpConfig()
        server1 = McpServerConfig("cmd1", [], {})
        server2 = McpServerConfig("cmd2", [], {})
        
        config.add_server("test", server1)
        with pytest.raises(ValueError, match="already exists"):
            config.add_server("test", server2, overwrite=False)
            
        assert config.servers["test"] == server1

    def test_add_server_overwrite(self):
        config = McpConfig()
        server1 = McpServerConfig("cmd1", [], {})
        server2 = McpServerConfig("cmd2", [], {})
        
        config.add_server("test", server1)
        config.add_server("test", server2, overwrite=True)
        
        assert config.servers["test"] == server2

    def test_save(self, tmp_path):
        path = tmp_path / "output.json"
        config = McpConfig()
        server = McpServerConfig("cmd", ["arg"], {"ENV": "VAL"})
        config.add_server("srv", server)
        
        config.save(path)
        
        assert path.exists()
        content = json.loads(path.read_text())
        assert content["mcpServers"]["srv"]["command"] == "cmd"
        assert path.read_text().endswith("\n")

class TestHighLevelFunctions:
    def test_get_edison_zen_config(self, tmp_path):
        config = get_edison_zen_config(tmp_path, use_script=False)
        assert config.command == "edison"
        assert "zen" in config.args
        assert config.env["ZEN_WORKING_DIR"] == str(tmp_path.resolve())

    def test_get_edison_zen_config_script(self, tmp_path):
        config = get_edison_zen_config(tmp_path, use_script=True)
        assert config.command.endswith("run-server.sh")
        assert config.env["ZEN_WORKING_DIR"] == str(tmp_path.resolve())

    def test_configure_mcp_json_creates_new(self, tmp_path):
        # Setup mocked template
        template_path = Path("src/edison/data/templates/mcp.json.template")
        
        # We need to mock the reading of the template since it might not exist yet
        # BUT since we are in RED phase, we expect failure anyway if template is missing
        # However, the function is supposed to load it. 
        
        # Let's just run it. The function configure_mcp_json should orchestrate everything.
        # We mock sys.stdout to keep output clean
        
        result = configure_mcp_json(
            project_root=tmp_path,
            config_file=".mcp.json",
            overwrite=False,
            dry_run=False
        )
        
        assert (tmp_path / ".mcp.json").exists()
        assert "edison-zen" in result["mcpServers"]

    def test_configure_mcp_json_dry_run(self, tmp_path):
        result = configure_mcp_json(
            project_root=tmp_path,
            config_file=".mcp.json",
            overwrite=False,
            dry_run=True
        )
        
        assert not (tmp_path / ".mcp.json").exists()
        assert "edison-zen" in result["mcpServers"]

    def test_configure_mcp_json_preserves_existing(self, tmp_path):
        existing = {
            "mcpServers": {
                "other": {"command": "other", "args": [], "env": {}}
            }
        }
        (tmp_path / ".mcp.json").write_text(json.dumps(existing))
        
        configure_mcp_json(tmp_path)
        
        content = json.loads((tmp_path / ".mcp.json").read_text())
        assert "other" in content["mcpServers"]
        assert "edison-zen" in content["mcpServers"]

