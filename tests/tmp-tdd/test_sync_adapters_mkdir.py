import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Imports for patching
from edison.core.adapters.sync.claude import ClaudeSync
from edison.core.adapters.sync.zen import ZenSync
from edison.core.adapters.sync.cursor import CursorSync

def test_claude_sync_mkdir(tmp_path):
    # Setup
    repo_root = tmp_path
    sync = ClaudeSync(repo_root=repo_root)
    
    # Action
    sync.validate_claude_structure()
    
    # Verify
    assert (repo_root / ".claude").exists()
    assert (repo_root / ".claude" / "agents").exists()

def test_zen_sync_mkdir(tmp_path):
    repo_root = tmp_path
    
    # Mock dependencies
    with patch('edison.core.adapters.sync.zen.ConfigManager') as MockConfig:
        with patch('edison.core.adapters.sync.zen.CompositionEngine'):
            with patch('edison.core.adapters.sync.zen.GuidelineRegistry'):
                with patch('edison.core.adapters.sync.zen.RulesRegistry'):
                    sync = ZenSync(repo_root=repo_root)
                    
                    # Mock active packs to be empty
                    sync._active_packs = lambda: []
                    # Mock prompt composition to return string
                    sync.compose_zen_prompt = lambda role, model, packs: "prompt content"
                    
                    # Action
                    sync.sync_role_prompts("codex", ["default"])
                    
                    # Verify
                    prompts_dir = repo_root / ".zen" / "conf" / "systemprompts" / "clink" / "project"
                    assert prompts_dir.exists()
                    assert (prompts_dir / "codex.txt").exists()

def test_cursor_sync_mkdir(tmp_path):
    repo_root = tmp_path
    config_dir = repo_root / ".edison"
    config_dir.mkdir()
    
    # Mock dependencies
    with patch('edison.core.adapters.sync.cursor.ConfigManager') as MockConfig:
        with patch('edison.core.adapters.sync.cursor.GuidelineRegistry'):
            with patch('edison.core.adapters.sync.cursor.RulesRegistry') as MockRules:
                mock_rules_instance = MockRules.return_value
                mock_rules_instance.compose.return_value = {"rules": {
                    "r1": {"id": "r1", "category": "validation"}
                }}
                
                sync = CursorSync(project_root=repo_root)
                
                # 1. Test _write_snapshot (called by sync_to_cursorrules)
                # We need to mock _render_cursorrules to return string
                sync._render_cursorrules = lambda: "content"
                sync.sync_to_cursorrules()
                
                cache_dir = config_dir / ".cache" / "cursor"
                assert cache_dir.exists()
                assert (cache_dir / "cursorrules.snapshot.md").exists()
                
                # 2. Test sync_structured_rules
                sync.sync_structured_rules()
                rules_dir = repo_root / ".cursor" / "rules"
                assert rules_dir.exists()
                
                # 3. Test sync_agents_to_cursor
                # Create source agent
                generated_agents = config_dir / "_generated" / "agents"
                generated_agents.mkdir(parents=True)
                (generated_agents / "agent1.md").write_text("content")
                
                sync.sync_agents_to_cursor()
                
                cursor_agents = repo_root / ".cursor" / "agents"
                assert cursor_agents.exists()
                assert (cursor_agents / "agent1.md").exists()

                # 4. Test _auto_compose_agents via direct call or mocking
                # It calls src_dir.mkdir
                # Let's test logic separately by removing generated dir
                # Actually _auto_compose_agents is called when sources are missing AND auto_compose=True
                # But it needs AgentRegistry
                with patch('edison.core.adapters.sync.cursor.AgentRegistry') as MockAgentRegistry:
                    mock_reg = MockAgentRegistry.return_value
                    mock_reg.discover_core_agents.return_value = {"agent2": "path"}
                    with patch('edison.core.adapters.sync.cursor.compose_agent', return_value="agent content"):
                        # Remove generated dir to trigger creation
                        import shutil
                        shutil.rmtree(generated_agents)
                        
                        # Trigger
                        sync.sync_agents_to_cursor(auto_compose=True)
                        
                        assert generated_agents.exists()
                        assert (generated_agents / "agent2.md").exists()

