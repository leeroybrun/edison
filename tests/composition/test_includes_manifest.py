import json
from pathlib import Path
from edison.core.composition import includes
from edison.core.composition.includes import _write_cache, _repo_root

def test_write_cache_updates_manifest(tmp_path, monkeypatch):
    # Mock _repo_root and _cache_dir to use tmp_path
    monkeypatch.setattr(includes, "_repo_root", lambda: tmp_path)
    
    # Mock _cache_dir to return a subdir of tmp_path
    cache_dir = tmp_path / "_generated" / "validators"
    monkeypatch.setattr(includes, "_cache_dir", lambda: cache_dir)

    # 1. First write
    deps = [tmp_path / "foo.txt"]
    # Create dummy file so relative_to works if needed, or just mock relative_to behavior
    # The code calls relative_to(_repo_root())
    (tmp_path / "foo.txt").touch()
    
    out_path = _write_cache("val1", "content1", deps, "hash1")
    
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8") == "content1"
    
    manifest = cache_dir / "manifest.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["val1"]["hash"] == "hash1"
    
    # 2. Second write (update)
    out_path2 = _write_cache("val2", "content2", [], "hash2")
    
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data["val1"]["hash"] == "hash1"
    assert data["val2"]["hash"] == "hash2"
