import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from edison.core.task import io as task_io
from edison.core.task import locking
from edison.core.utils.io import ensure_directory as ensure_dir

# ----------------------------------------------------------------------
# Tests for src/edison/core/task/io.py
# ----------------------------------------------------------------------

def test_io_create_task_ensures_dir(tmp_path):
    """Verify create_task creates directory via _write."""
    tasks_root = tmp_path / "tasks"
    
    with patch("edison.core.task.io._tasks_root", return_value=tasks_root), \
         patch("edison.core.task.io.create_qa_brief"):
        
        task_io.create_task("t1", "title")
        
        # Verify file and parent dir exist
        # Default status is 'todo' usually, but we just check if it was created
        # The path construction depends on TYPE_INFO["task"]["default_status"] which is imported.
        # We assume 'todo' or we find the file.
        created_files = list(tasks_root.glob("**/*.md"))
        assert len(created_files) > 0
        assert created_files[0].parent.exists()

def test_io_claim_task_ensures_dirs(tmp_path):
    """Verify claim_task creates task and QA directories."""
    # Setup src paths
    tasks_root = tmp_path / "tasks"
    qa_root = tmp_path / "qa"
    
    # Create source task
    task_src_dir = tasks_root / "todo"
    task_src_dir.mkdir(parents=True)
    (task_src_dir / "task-t1.md").write_text("status: todo", encoding="utf-8")
    
    # Create source QA
    qa_src_dir = qa_root / "waiting"
    qa_src_dir.mkdir(parents=True)
    (qa_src_dir / "t1-qa.md").write_text("status: waiting", encoding="utf-8")
    
    # Destinations
    session_tasks_dir = tmp_path / "session" / "tasks" / "wip"
    session_qa_dir = tmp_path / "session" / "qa" / "todo" # default for claim might be different? 
    # Actually claim_task uses _session_qa_dir(session_id, default_qa)
    # We mock _session_tasks_dir and _session_qa_dir
    
    with patch("edison.core.task.io._tasks_root", return_value=tasks_root), \
         patch("edison.core.task.io._qa_root", return_value=qa_root), \
         patch("edison.core.task.io._session_tasks_dir", return_value=session_tasks_dir), \
         patch("edison.core.task.io._session_qa_dir", return_value=session_qa_dir):
             
        task_io.claim_task("t1", "session1")
        
        assert session_tasks_dir.exists()
        assert (session_tasks_dir / "task-t1.md").exists()
        
        assert session_qa_dir.exists()
        assert (session_qa_dir / "t1-qa.md").exists()

def test_io_ready_task_ensures_dirs(tmp_path):
    """Verify ready_task creates directories."""
    # Setup src (in session wip)
    session_tasks_wip = tmp_path / "sess" / "tasks" / "wip"
    session_tasks_wip.mkdir(parents=True)
    (session_tasks_wip / "task-t1.md").write_text("status: wip", encoding="utf-8")
    
    # Setup QA (in session default/waiting?)
    # ready_task logic: qa_src = _session_qa_dir(..., default_qa)
    # We assume default_qa is 'waiting' or similar.
    # Let's just mock the dirs returned.
    
    session_tasks_done = tmp_path / "sess" / "tasks" / "done"
    session_qa_src = tmp_path / "sess" / "qa" / "waiting"
    session_qa_src.mkdir(parents=True)
    (session_qa_src / "t1-qa.md").write_text("qa", encoding="utf-8")
    
    session_qa_todo = tmp_path / "sess" / "qa" / "todo"
    
    with patch("edison.core.task.io._session_tasks_dir", side_effect=lambda sid, st: session_tasks_wip if st == "wip" else session_tasks_done), \
         patch("edison.core.task.io._session_qa_dir", side_effect=lambda sid, st: session_qa_src if "waiting" in str(st) else session_qa_todo), \
         patch("edison.core.task.io.get_semantic_state", side_effect=lambda d, s: s), \
         patch("edison.core.task.io._qa_root"):
         
         # We need to be careful with get_semantic_state values matching our mocks
         # The code:
         # wip_status = get_semantic_state("task", "wip") -> "wip"
         # done_status = get_semantic_state("task", "done") -> "done"
         
         task_io.ready_task("t1", "sess1")
         
         assert session_tasks_done.exists()
         assert (session_tasks_done / "task-t1.md").exists()
         
         assert session_qa_todo.exists()
         assert (session_qa_todo / "t1-qa.md").exists()

def test_io_qa_progress_ensures_dir(tmp_path):
    """Verify qa_progress creates dest dir."""
    qa_root = tmp_path / "qa"
    src_dir = qa_root / "todo"
    src_dir.mkdir(parents=True)
    (src_dir / "t1-qa.md").write_text("content")
    
    dst_dir = qa_root / "wip"
    
    with patch("edison.core.task.io._qa_root", return_value=qa_root):
        task_io.qa_progress("t1", "todo", "wip")
        
        assert dst_dir.exists()
        assert (dst_dir / "t1-qa.md").exists()

def test_io_record_tdd_evidence_ensures_dir(tmp_path):
    """Verify record_tdd_evidence creates dir."""
    # Mock get_management_paths
    mock_mgmt = MagicMock()
    mock_mgmt.get_qa_root.return_value = tmp_path / "mgmt_qa"
    
    with patch("edison.core.task.io.get_management_paths", return_value=mock_mgmt):
        task_io.record_tdd_evidence("t1", "red", "note")
        
        evidence_path = tmp_path / "mgmt_qa" / "validation-evidence" / "tasks" / "task-t1.tdd.md"
        assert evidence_path.exists()
        assert evidence_path.parent.exists()

# ----------------------------------------------------------------------
# Tests for src/edison/core/task/locking.py
# ----------------------------------------------------------------------

def test_locking_safe_move_file_ensures_dir(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("A")
    dst = tmp_path / "sub" / "b.txt"
    
    locking.safe_move_file(src, dst)
    
    assert dst.exists()
    assert dst.parent.exists()
    assert dst.read_text() == "A"

def test_locking_write_text_locked_ensures_dir(tmp_path):
    target = tmp_path / "locked" / "file.txt"
    
    locking.write_text_locked(target, "content")
    
    assert target.exists()
    assert target.parent.exists()
    assert target.read_text() == "content"
