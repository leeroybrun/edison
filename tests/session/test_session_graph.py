import os
import pytest
import yaml
import json
from pathlib import Path
from edison.core.session import graph
from edison.core.session import store
from edison.core.config.domains import SessionConfig

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root.
    """
    # Setup .edison/core/config
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)
    
    defaults_data = {
        "edison": {"version": "1.0.0"},
        "file_locking": {
            "timeout_seconds": 1,
            "poll_interval_seconds": 0.1,
            "fail_open": False
        }
    }
    (config_dir / "defaults.yaml").write_text(yaml.dump(defaults_data))
    
    session_data = {
        "session": {
            "paths": {
                "root": ".project/sessions",
            },
            "validation": {
                "idRegex": r"^[a-zA-Z0-9_\-\.]+$",
                "maxLength": 64
            },
            "states": {
                "active": "active",
                "closing": "closing",
                "validated": "validated"
            }
        }
    }
    (config_dir / "session.yaml").write_text(yaml.dump(session_data))
    
    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    
    # Reload configs
    store._CONFIG = SessionConfig()
    
    return tmp_path

def test_register_task(project_root):
    """Test registering a task in the session graph."""
    sid = "sess-graph-task"
    store._ensure_session_dirs()
    sess_dir = store._session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "session.json").write_text("{}")
    
    graph.register_task(sid, "task-1", owner="me", status="todo")
    
    data = json.loads((sess_dir / "session.json").read_text())
    assert "tasks" in data
    assert "task-1" in data["tasks"]
    assert data["tasks"]["task-1"]["owner"] == "me"
    assert data["tasks"]["task-1"]["status"] == "todo"

def test_register_qa(project_root):
    """Test registering a QA entry."""
    sid = "sess-graph-qa"
    store._ensure_session_dirs()
    sess_dir = store._session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "session.json").write_text("{}")
    
    graph.register_qa(sid, "task-1", "qa-1", status="waiting")
    
    data = json.loads((sess_dir / "session.json").read_text())
    assert "qa" in data
    assert "qa-1" in data["qa"]
    assert data["qa"]["qa-1"]["taskId"] == "task-1"
    
    # Check task linkage
    assert "tasks" in data
    assert "task-1" in data["tasks"]
    assert data["tasks"]["task-1"]["qaId"] == "qa-1"

def test_link_tasks(project_root):
    """Test linking tasks."""
    sid = "sess-graph-link"
    store._ensure_session_dirs()
    sess_dir = store._session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "session.json").write_text("{}")
    
    graph.link_tasks(sid, "parent", "child")
    
    data = json.loads((sess_dir / "session.json").read_text())
    assert "parent" in data["tasks"]
    assert "child" in data["tasks"]
    assert "child" in data["tasks"]["parent"]["childIds"]
    assert data["tasks"]["child"]["parentId"] == "parent"

def test_gather_cluster(project_root):
    """Test gathering a cluster."""
    sid = "sess-graph-cluster"
    store._ensure_session_dirs()
    sess_dir = store._session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "session.json").write_text("{}")
    
    graph.link_tasks(sid, "root", "c1")
    graph.link_tasks(sid, "root", "c2")
    graph.link_tasks(sid, "c1", "gc1")
    
    sess = store.load_session(sid)
    cluster = graph.gather_cluster(sess, "root")
    
    ids = {item["taskId"] for item in cluster}
    assert ids == {"root", "c1", "c2", "gc1"}
