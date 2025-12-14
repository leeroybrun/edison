import pytest
import yaml
from pathlib import Path
from edison.core.session import lifecycle
from edison.core.session.lifecycle import manager
from edison.core.session.persistence.repository import SessionRepository
from edison.core.state.guards import registry as guard_registry
from edison.core.state.conditions import registry as condition_registry
from edison.core.state.actions import registry as action_registry
from tests.helpers.cache_utils import reset_edison_caches

def session_exists(session_id: str) -> bool:
    """Check if a session exists."""
    repo = SessionRepository()
    return repo.exists(session_id)

@pytest.fixture(autouse=True)
def setup_custom_config(project_root):
    """Setup custom session configuration and registries."""
    # Setup .edison/config
    config_dir = project_root / ".edison" / "config"
    
    defaults_data = {
        "edison": {"version": "1.0.0"},
        "file_locking": {
            "timeout_seconds": 1,
            "poll_interval_seconds": 0.1,
            "fail_open": False
        }
    }
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))
    
    session_data = {
        "session": {
            "paths": {
                "root": ".project/sessions",
            },
            "validation": {
                "idRegex": r"^[a-zA-Z0-9_\-\.]+$",
                "maxLength": 64,
            },
            "states": {
                "active": "active",
                "closing": "closing",
                "validated": "validated",
            },
            "defaults": {
                "initialState": "active",
            },
        },
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data))

    # Canonical state machine config lives under workflow.statemachine.
    workflow_cfg = {
        "workflow": {
            "statemachine": {
                "session": {
                    "states": {
                        "active": {
                            "initial": True,
                            "allowed_transitions": [
                                {"to": "closing", "guard": "always_allow"},
                            ],
                        },
                        "closing": {
                            "allowed_transitions": [
                                {"to": "closed", "conditions": [{"name": "ready_to_close"}]},
                            ],
                        },
                        "closed": {"final": True, "allowed_transitions": []},
                    },
                },
            }
        }
    }
    (config_dir / "workflow.yml").write_text(yaml.dump(workflow_cfg))

    # IMPORTANT: Module imports above may have already loaded config defaults
    # before these files were written. Reset caches so subsequent calls pick up
    # the freshly written project config.
    reset_edison_caches()
    
    # Reset registries and reload configs
    guard_registry.reset()
    condition_registry.reset()
    action_registry.reset()
    guard_registry.register("always_allow", lambda ctx: True)
    condition_registry.register("ready_to_close", lambda ctx: True)
    action_registry.register("record_closed", lambda ctx: None)

def test_create_session(project_root):
    """Test creating a new session via manager."""
    sid = "sess-mgr-create"
    
    # Should return session path
    sess_path = manager.create_session(sid, owner="me", create_wt=False)
    sess = manager.get_session(sid)
    
    assert sess["id"] == sid
    assert sess["meta"]["owner"] == "me"
    # State may be "Active" or "active" depending on implementation
    assert sess["state"].lower() == "active"
    
    # Verify it exists on disk
    assert session_exists(sid)

def test_get_session(project_root):
    """Test retrieving a session."""
    sid = "sess-mgr-get"
    manager.create_session(sid, owner="me", create_wt=False)
    
    sess = manager.get_session(sid)
    assert sess["id"] == sid

def test_transition_session(project_root):
    """Test transitioning session state."""
    sid = "sess-mgr-trans"
    manager.create_session(sid, owner="me", create_wt=False)
    
    # Transition to closing
    manager.transition_session(sid, "closing")
    
    sess = manager.get_session(sid)
    assert sess["state"].lower() == "closing"
    
    # Verify file moved to closing dir
    closing_dir = project_root / ".project" / "sessions" / "closing" / sid
    assert (closing_dir / "session.json").exists()

def test_list_sessions(project_root):
    """Test listing sessions."""
    manager.create_session("s1", owner="me", create_wt=False)
    manager.create_session("s2", owner="me", create_wt=False)
    
    sessions = manager.list_sessions(state="active")
    assert "s1" in sessions
    assert "s2" in sessions


def test_render_markdown_includes_session_scoped_qa(project_root):
    """render_markdown must resolve QA IDs as <task_id>-qa (not <task_id>)."""
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository
    from edison.core.qa.models import QARecord
    from edison.core.qa.workflow.repository import QARepository

    sid = "sess-md-qa"
    manager.create_session(sid, owner="me", create_wt=False)

    task_id = "150-wave1-demo"
    task_repo = TaskRepository(project_root=project_root)
    task = Task.create(
        task_id=task_id,
        title="Demo task",
        session_id=sid,
        owner="me",
        state="wip",
    )
    task_repo.save(task)

    qa_repo = QARepository(project_root=project_root)
    qa_id = f"{task_id}-qa"
    qa = QARecord.create(
        qa_id=qa_id,
        task_id=task_id,
        title=f"QA for {task_id}",
        session_id=sid,
        state="waiting",
    )
    qa_repo.save(qa)

    sess = manager.get_session(sid)
    md = manager.render_markdown(sess)
    assert qa_id in md
