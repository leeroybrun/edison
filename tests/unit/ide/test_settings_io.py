import json
from pathlib import Path
from edison.core.adapters.components.settings import SettingsComposer

def test_write_settings_file_creates_json(tmp_path):
    # Setup SettingsComposer with tmp_path as repo_root
    composer = SettingsComposer(repo_root=tmp_path)
    
    # write_settings_file writes to .claude/settings.json
    out_path = composer.write_settings_file()
    
    assert out_path.exists()
    assert out_path.name == "settings.json"
    assert out_path.parent.name == ".claude"
    
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
