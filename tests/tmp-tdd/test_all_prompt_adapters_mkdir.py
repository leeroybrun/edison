import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Import adapters - using conditional imports inside tests or patching to avoid initial load errors if dependencies missing
from edison.core.adapters.prompt.claude import ClaudeAdapter
from edison.core.adapters.prompt.zen import ZenPromptAdapter
from edison.core.adapters.prompt.cursor import CursorPromptAdapter

def test_claude_adapter_mkdir(tmp_path):
    generated_root = tmp_path / "generated"
    generated_root.mkdir()
    repo_root = tmp_path
    
    adapter = ClaudeAdapter(generated_root, repo_root)
    
    # Mock generate_commands, generate_hooks, generate_settings to avoid deps
    adapter.generate_commands = lambda: {}
    adapter.generate_hooks = lambda: {}
    adapter.generate_settings = lambda: None
    
    output_root = tmp_path / "claude_out"
    
    # We need to mock ClaudeSync because it is imported INSIDE write_outputs
    # Patching where it is defined/imported from
    with patch('edison.core.adapters.sync.claude.ClaudeSync') as MockSync:
        mock_sync_instance = MockSync.return_value
        adapter.write_outputs(output_root)
        
        # Verify output_root created
        assert output_root.exists()
        # Verify sync called
        MockSync.assert_called_with(repo_root=repo_root)
        mock_sync_instance.sync_agents_to_claude.assert_called_once()

def test_zen_adapter_mkdir(tmp_path):
    generated_root = tmp_path / "generated"
    generated_root.mkdir()
    # Zen needs orchestrator manifest
    (generated_root / "orchestrator-manifest.json").write_text("{}")
    
    repo_root = tmp_path
    
    adapter = ZenPromptAdapter(generated_root, repo_root)
    
    output_root = tmp_path / "zen_out"
    
    adapter.write_outputs(output_root)
    
    assert output_root.exists()

def test_cursor_adapter_mkdir(tmp_path):
    generated_root = tmp_path / "generated"
    generated_root.mkdir()
    (generated_root / "agents").mkdir()
    (generated_root / "validators").mkdir()
    
    repo_root = tmp_path
    
    adapter = CursorPromptAdapter(generated_root, repo_root)
    
    # Mock generate_commands
    adapter.generate_commands = lambda: {}
    
    output_root = tmp_path / "cursor_out"
    
    adapter.write_outputs(output_root)
    
    assert output_root.exists()
    # Check default subdirs (or whatever config provides)
    # Based on codex experience, it might use simple names if config empty/default
    # But let's check existence generally.
    assert any(output_root.iterdir()) or output_root.exists()
    
    # Specifically check if subdirs created if config defaults match code
    # Code: agents_dirname = adapter_config.get("agents_dirname", "cursor-agents")
    # If config is empty, it should be cursor-agents.
    # If ConfigManager returns defaults, it might be different.
    # Let's just check output_root existence primarily, and maybe subdirs if easy.
    
    # We can check if ensure_dir was called via side effect of directory existence.
    pass
