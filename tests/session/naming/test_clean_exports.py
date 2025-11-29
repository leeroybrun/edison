"""Test clean session module exports.

This test ensures that session module only exports approved symbols
and that legacy exports (store, graph, layout, api) have been removed.
"""
from __future__ import annotations


def test_session_module_exports_approved_symbols():
    """session module exports only approved symbols."""
    from edison.core import session

    # Approved exports that MUST be present
    assert hasattr(session, 'SessionManager'), "SessionManager must be exported"
    assert hasattr(session, 'validate_session_id'), "validate_session_id must be exported"
    assert hasattr(session, 'SessionIdError'), "SessionIdError must be exported"
    assert hasattr(session, 'create_session'), "create_session must be exported"
    assert hasattr(session, 'get_session'), "get_session must be exported"
    assert hasattr(session, 'list_sessions'), "list_sessions must be exported"
    assert hasattr(session, 'transition_session'), "transition_session must be exported"
    assert hasattr(session, 'get_current_session'), "get_current_session must be exported"
    assert hasattr(session, 'set_current_session'), "set_current_session must be exported"
    assert hasattr(session, 'clear_current_session'), "clear_current_session must be exported"
    assert hasattr(session, 'models'), "models submodule must be exported"


def test_session_module_no_legacy_exports():
    """session module does not export legacy symbols via __all__."""
    from edison.core import session

    # Check that legacy modules are not in __all__ (the public API)
    all_exports = set(session.__all__)
    assert 'store' not in all_exports, "Legacy 'store' must not be in __all__"
    assert 'graph' not in all_exports, "Legacy 'graph' must not be in __all__"
    assert 'layout' not in all_exports, "Legacy 'layout' must not be in __all__"
    assert 'api' not in all_exports, "Legacy 'api' must not be in __all__"


def test_validate_session_id_is_from_id_module():
    """validate_session_id comes from session.id module."""
    from edison.core import session
    from edison.core.session.id import validate_session_id as id_validate

    # They should be the same function
    assert session.validate_session_id is id_validate


def test_session_id_error_is_from_id_module():
    """SessionIdError comes from session.id module."""
    from edison.core import session
    from edison.core.session.id import SessionIdError as id_error

    # They should be the same class
    assert session.SessionIdError is id_error
