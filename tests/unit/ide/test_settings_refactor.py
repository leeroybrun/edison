
import pytest
from pathlib import Path
from edison.core.adapters.components.settings import SettingsComposer

def test_write_settings_file_resilience_to_bad_encoding(tmp_path):
    """
    Strict TDD: Verify that write_settings_file is resilient to invalid encoding 
    in the existing settings file.
    
    Current behavior: potentially crashes on UnicodeDecodeError (unhandled).
    Desired behavior: catch error via read_json_safe and overwrite/continue safely.
    """
    # Setup repo root
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    
    # Setup .claude directory and bad settings file
    claude_dir = repo_root / ".claude"
    claude_dir.mkdir()
    bad_settings = claude_dir / "settings.json"
    
    # Write invalid UTF-8 bytes
    with open(bad_settings, "wb") as f:
        f.write(b"\x80\x81\xff") # Invalid start bytes for UTF-8
        
    # Instantiate composer with backup disabled to hit the JSON load line directly
    config = {
        "settings": {
            "claude": {
                "backup_before": False
            }
        }
    }
    composer = SettingsComposer(config=config, repo_root=repo_root)
    
    # Execute - this should NOT raise UnicodeDecodeError
    try:
        composer.write_settings_file()
    except UnicodeDecodeError:
        pytest.fail("write_settings_file crashed on invalid UTF-8 in existing settings.json (at json load step)")
    except Exception as e:
        # We ignore other exceptions (like from ConfigManager) as we focus on the JSON load
        pass
        
    # Verify file was replaced or handled
    assert bad_settings.exists()
    # New content should be valid text
    content = bad_settings.read_text(encoding="utf-8")
    assert "{" in content
