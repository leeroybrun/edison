import pytest
import json
from pathlib import Path
from edison.core.setup.discovery import SetupDiscovery

class MockSetupDiscovery(SetupDiscovery):
    """Subclass to access private methods or test them."""
    def load_json_public(self, path):
        return self._load_json(path)

def test_load_json_migration(tmp_path):
    """Test _load_json behavior."""
    # We need to mock SetupDiscovery.__init__ because it loads config
    # But we can just pass dummy paths
    
    edison_core = tmp_path / "core"
    repo_root = tmp_path / "repo"
    edison_core.mkdir()
    repo_root.mkdir()
    
    # Setup mock setup.yaml so init works
    (edison_core / "config").mkdir()
    (edison_core / "config" / "setup.yaml").write_text("setup: {}")
    
    discoverer = MockSetupDiscovery(edison_core, repo_root)
    
    path = tmp_path / "test.json"
    
    # Case 1: Valid
    path.write_text('{"key": "value"}')
    assert discoverer.load_json_public(path) == {"key": "value"}
    
    # Case 2: Invalid
    path.write_text('{invalid')
    assert discoverer.load_json_public(path) == {}
    
    # Case 3: Missing
    assert discoverer.load_json_public(tmp_path / "missing.json") == {}
