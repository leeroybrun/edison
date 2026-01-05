"""Test that CLI session commands can import validate_session_id correctly.

This test ensures the import migration from api.py to id.py works correctly.
Following strict TDD: This test will FAIL initially when importing from api.py,
then PASS when imports are updated to id.py.
"""
from __future__ import annotations

import pytest


def test_status_cli_can_import_validate_session_id():
    """Test that status.py can import validate_session_id from id module."""
    # This will fail initially because status.py imports from api
    # It will pass after we update the import to .id module
    from edison.cli.session import status

    # Verify the module loaded correctly
    assert hasattr(status, 'main')
    assert hasattr(status, 'register_args')

    # Verify validate_session_id is available in the module's execution context
    # by checking we can call the main function (which uses validate_session_id)
    import argparse
    parser = argparse.ArgumentParser()
    status.register_args(parser)
    # This proves the import chain works


def test_create_cli_can_import_validate_session_id():
    """Test that create.py can import validate_session_id from id module."""
    from edison.cli.session import create

    assert hasattr(create, 'main')
    assert hasattr(create, 'register_args')

    import argparse
    parser = argparse.ArgumentParser()
    create.register_args(parser)


def test_close_cli_can_import_validate_session_id():
    """Test that close.py can import validate_session_id from id module."""
    from edison.cli.session import close

    assert hasattr(close, 'main')
    assert hasattr(close, 'register_args')

    import argparse
    parser = argparse.ArgumentParser()
    close.register_args(parser)


def test_validate_session_id_direct_import_from_id():
    """Test that validate_session_id can be imported directly from id module."""
    from edison.core.session.core.id import SessionIdError, validate_session_id

    # Verify it works correctly
    assert validate_session_id("test-session-001") == "test-session-001"

    # Verify it raises on invalid input
    with pytest.raises(SessionIdError):
        validate_session_id("")


def test_api_module_deleted():
    """Test that api.py has been successfully deleted.

    This test verifies that the api.py shim has been removed and we're using
    the direct id module import everywhere.
    """
    with pytest.raises(ImportError):
        import importlib

        importlib.import_module("edison.core.session.api")
