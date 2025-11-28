"""Test that session ID aliases have been removed.

Following strict TDD and principle 3 (NO LEGACY),
we verify that all backward compatibility aliases
have been completely removed from session/id.py.
"""
import pytest


def test_sanitize_session_id_alias_removed():
    """Verify sanitize_session_id alias no longer exists."""
    from edison.core.session import id as session_id_module

    assert not hasattr(session_id_module, 'sanitize_session_id'), (
        "sanitize_session_id alias should be removed. "
        "Use validate_session_id instead."
    )


def test_normalize_session_id_alias_removed():
    """Verify normalize_session_id alias no longer exists."""
    from edison.core.session import id as session_id_module

    assert not hasattr(session_id_module, 'normalize_session_id'), (
        "normalize_session_id alias should be removed. "
        "Use validate_session_id instead."
    )


def test_session_id_public_api():
    """Verify the correct public API is exported."""
    from edison.core.session import id as session_id_module

    # Should have these
    assert hasattr(session_id_module, 'validate_session_id')
    assert hasattr(session_id_module, 'detect_session_id')
    assert hasattr(session_id_module, 'SessionIdError')

    # Should NOT have these
    assert not hasattr(session_id_module, 'sanitize_session_id')
    assert not hasattr(session_id_module, 'normalize_session_id')


def test___all___does_not_export_aliases():
    """Verify __all__ doesn't export the removed aliases."""
    from edison.core.session.id import __all__

    assert 'validate_session_id' in __all__
    assert 'detect_session_id' in __all__
    assert 'SessionIdError' in __all__

    # Aliases should not be exported
    assert 'sanitize_session_id' not in __all__
    assert 'normalize_session_id' not in __all__
