import json
import pytest
from pathlib import Path
from edison.core.adapters.sync.cursor import CursorSync

def test_write_snapshot_creates_meta_json(tmp_path):
    # Setup CursorSync with tmp_path as repo_root
    # We don't need real config/registries for this unit test
    sync = CursorSync(project_root=tmp_path, config={})
    
    content = "some content"
    hash_val = "abc123hash"
    
    sync._write_snapshot(content, hash_val)
    
    # Check snapshot file
    snapshot_path = tmp_path / ".edison" / ".cache" / "cursor" / "cursorrules.snapshot.md"
    assert snapshot_path.exists()
    assert snapshot_path.read_text(encoding="utf-8") == content
    
    # Check meta file
    meta_path = tmp_path / ".edison" / ".cache" / "cursor" / "cursorrules.meta.json"
    assert meta_path.exists()
    
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert data["hash"] == hash_val
    assert "generatedAt" in data
