
import pytest
from pathlib import Path
import json
from edison.core.qa import bundler, store

def test_bundler_creates_directory(tmp_path):
    """Test that write_bundle_summary creates the parent directory."""
    # Setup
    task_id = "t-022-bundler"
    round_num = 1
    summary = {"status": "ok"}
    
    # Using tmp_path as base for evidence dir requires mocking or patching
    # evidence.get_evidence_dir usually returns a path relative to project root
    # For isolation, we can monkeypatch bundler.evidence.get_evidence_dir
    
    base_dir = tmp_path / "evidence"
    
    # Mocking get_evidence_dir to return our tmp path
    orig_get_evidence_dir = bundler.evidence.get_evidence_dir
    bundler.evidence.get_evidence_dir = lambda tid: base_dir / tid
    
    try:
        # Action
        path = bundler.write_bundle_summary(task_id, round_num, summary)
        
        # Assert
        assert path.parent.exists()
        assert path.parent.is_dir()
        assert path.exists()
        assert json.loads(path.read_text()) == summary
    finally:
        # Restore
        bundler.evidence.get_evidence_dir = orig_get_evidence_dir

def test_store_creates_directory(tmp_path):
    """Test that append_jsonl creates the parent directory."""
    target_file = tmp_path / "nested" / "dir" / "data.jsonl"
    data = {"foo": "bar"}
    
    assert not target_file.parent.exists()
    
    store.append_jsonl(target_file, data)
    
    assert target_file.parent.exists()
    assert target_file.exists()
    lines = target_file.read_text().strip().split('\n')
    assert len(lines) == 1
    assert json.loads(lines[0]) == data
