import pytest
import types

def test_store_is_package():
    """Verify that store is converted to a package."""
    from edison.core.session import store
    # If it's a package, it should have a __path__
    assert hasattr(store, "__path__"), "edison.core.session.store should be a package (directory)"

def test_persistence_module_structure():
    """Verify persistence module structure and exports."""
    from edison.core.session.store import persistence
    
    assert hasattr(persistence, "load_session")
    assert hasattr(persistence, "save_session")
    # Internal functions mentioned in prompt
    assert hasattr(persistence, "_read_json")
    assert hasattr(persistence, "_write_json")

def test_discovery_module_structure():
    """Verify discovery module structure and exports."""
    from edison.core.session.store import discovery
    
    assert hasattr(discovery, "session_exists")
    assert hasattr(discovery, "get_session_json_path")
    assert hasattr(discovery, "auto_session_for_owner")
    # Internal functions mentioned in prompt
    assert hasattr(discovery, "_list_active_sessions")

def test_lifecycle_module_structure():
    """Verify lifecycle module structure and exports."""
    from edison.core.session.store import lifecycle
    
    assert hasattr(lifecycle, "ensure_session")
    assert hasattr(lifecycle, "transition_state")
    assert hasattr(lifecycle, "acquire_session_lock")
    # Internal functions mentioned in prompt
    assert hasattr(lifecycle, "_move_session_json_to")

def test_store_public_api_reexports():
    """Verify that the top-level store package re-exports all public functions."""
    from edison.core.session import store
    
    # From persistence
    assert hasattr(store, "load_session")
    assert hasattr(store, "save_session")
    
    # From discovery
    assert hasattr(store, "session_exists")
    assert hasattr(store, "get_session_json_path")
    assert hasattr(store, "auto_session_for_owner")
    
    # From lifecycle
    assert hasattr(store, "ensure_session")
    assert hasattr(store, "transition_state")
    assert hasattr(store, "acquire_session_lock")

def test_store_all_definition():
    """Verify __all__ is correctly defined."""
    from edison.core.session import store
    
    assert hasattr(store, "__all__")
    
    expected_exports = {
        "load_session",
        "save_session",
        "session_exists",
        "get_session_json_path",
        "auto_session_for_owner",
        "ensure_session",
        "transition_state",
        "acquire_session_lock",
    }
    
    for export in expected_exports:
        assert export in store.__all__
