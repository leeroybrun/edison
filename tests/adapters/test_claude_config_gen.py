import json
from pathlib import Path
from edison.core.adapters.sync.claude import ClaudeSync

def test_generate_claude_config_writes_json(tmp_path):
    # Setup ClaudeSync with tmp_path as repo_root
    sync = ClaudeSync(repo_root=tmp_path)
    
    # Pre-create necessary dirs (validate_claude_structure)
    (tmp_path / ".claude" / "agents").mkdir(parents=True)
    
    out_path = sync.generate_claude_config()
    
    assert out_path.exists()
    assert out_path.name == "config.json"
    
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["version"] == "1.0.0"
    assert "agents" in data
