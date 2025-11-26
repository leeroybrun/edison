import pytest
from pathlib import Path
from edison.core.adapters.prompt.codex import CodexAdapter

def test_codex_adapter_creates_directories(tmp_path):
    # Setup
    generated_root = tmp_path / "generated"
    generated_root.mkdir()
    (generated_root / "agents").mkdir()
    (generated_root / "validators").mkdir()
    
    # Create dummy agent/validator to trigger loops (though mkdir happens before)
    (generated_root / "agents" / "agent1.md").write_text("content")
    (generated_root / "validators" / "validator1.md").write_text("content")
    
    # Initialize adapter
    adapter = CodexAdapter(generated_root, repo_root=tmp_path)
    # Mock generate_commands to avoid import error for missing module
    adapter.generate_commands = lambda: {}
    
    # Define output root
    output_root = tmp_path / "codex_output"
    
    # Action
    adapter.write_outputs(output_root)
    
    # Verification
    assert output_root.exists()
    # ConfigManager seems to return 'agents' and 'validators' by default or via some found config
    # checking for what is actually created
    assert (output_root / "agents").exists()
    assert (output_root / "validators").exists()
