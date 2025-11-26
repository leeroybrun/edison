import pytest
import yaml
from pathlib import Path
from edison.core.session import manager
from edison.core.session import store
from edison.core.session._config import reset_config_cache
from edison.core.config.cache import clear_all_caches
from edison.core.state.guards import registry as guard_registry
from edison.core.state.conditions import registry as condition_registry
from edison.core.state.actions import registry as action_registry
import edison.core.utils.paths.resolver as path_resolver

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root.
    """
    # Reset ALL caches first
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    # Setup .edison/core/config
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)
    
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
                "maxLength": 64
            },
            "states": {
                "active": "active",
                "closing": "closing",
                "validated": "validated"
            },
            "defaults": {
                "initialState": "active"
            }
        },
        "statemachine": {
            "session": {
                "states": {
                    "active": {
                        "initial": True,
                        "allowed_transitions": [
                            {"to": "closing", "guard": "always_allow"}
                        ],
                    },
                    "closing": {
                        "allowed_transitions": [
                            {"to": "closed", "conditions": [{"name": "ready_to_close"}]}
                        ]
                    },
                    "closed": {"final": True, "allowed_transitions": []}
                }
            }
        }
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data))
    
    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    
    # Reset registries and reload configs
    guard_registry.reset()
    condition_registry.reset()
    action_registry.reset()
    guard_registry.register("always_allow", lambda ctx: True)
    condition_registry.register("ready_to_close", lambda ctx: True)
    action_registry.register("record_closed", lambda ctx: None)

    # Reset caches AFTER env vars are set
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()
    store.reset_session_store_cache()
    
    # Reset state machine
    from edison.core.session import state as session_state
    session_state._STATE_MACHINE = None
    
    yield tmp_path

    # Cleanup
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

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
    assert store.session_exists(sid)

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
