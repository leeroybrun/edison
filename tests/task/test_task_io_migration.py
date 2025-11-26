import json
from pathlib import Path
from edison.core.task import io

def test_task_records_io(tmp_path, monkeypatch):
    # Mock _tasks_meta_root
    monkeypatch.setattr(io, "_tasks_meta_root", lambda: tmp_path)
    
    # Test create_task_record
    rec = io.create_task_record("t1", "Task 1")
    path = tmp_path / "t1.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["id"] == "t1"
    assert data["title"] == "Task 1"
    
    # Test update_task_record
    io.update_task_record("t1", {"status": "done"})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "done"
    assert data["operation"] == "update"
