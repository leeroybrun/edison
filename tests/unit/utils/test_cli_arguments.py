"""
Tests for CLI argument parsing helpers.

This module tests argparse parent parsers and common argument helpers that
were extracted from the original cli.py god file.

Following STRICT TDD: These tests are written FIRST (RED phase) before
the implementation exists.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest


def test_parse_common_args_adds_json_flag() -> None:
    """parse_common_args should add --json flag."""
    from edison.core.utils.cli.arguments import parse_common_args

    parser = argparse.ArgumentParser()
    parse_common_args(parser)

    # Parse with --json flag
    args = parser.parse_args(["--json"])
    assert args.json is True

    # Parse without --json flag
    args_no_json = parser.parse_args([])
    assert args_no_json.json is False


def test_parse_common_args_adds_yes_flag() -> None:
    """parse_common_args should add -y/--yes flag."""
    from edison.core.utils.cli.arguments import parse_common_args

    parser = argparse.ArgumentParser()
    parse_common_args(parser)

    # Short form
    args_short = parser.parse_args(["-y"])
    assert args_short.yes is True

    # Long form
    args_long = parser.parse_args(["--yes"])
    assert args_long.yes is True

    # Without flag
    args_no = parser.parse_args([])
    assert args_no.yes is False


def test_parse_common_args_adds_repo_root_flag() -> None:
    """parse_common_args should add --repo-root flag with Path type."""
    from edison.core.utils.cli.arguments import parse_common_args

    parser = argparse.ArgumentParser()
    parse_common_args(parser)

    # With repo-root specified
    args = parser.parse_args(["--repo-root", "/tmp/test"])
    assert isinstance(args.repo_root, Path)
    assert args.repo_root == Path("/tmp/test")

    # Without repo-root
    args_no = parser.parse_args([])
    assert args_no.repo_root is None


def test_parse_common_args_returns_parser() -> None:
    """parse_common_args should return the parser for chaining."""
    from edison.core.utils.cli.arguments import parse_common_args

    parser = argparse.ArgumentParser()
    result = parse_common_args(parser)

    assert result is parser


def test_session_parent_creates_session_flag_optional() -> None:
    """session_parent should create a parent parser with optional --session flag."""
    from edison.core.utils.cli.arguments import session_parent

    parent = session_parent()
    parser = argparse.ArgumentParser(parents=[parent])

    # Should parse without --session
    args_no = parser.parse_args([])
    assert args_no.session is None

    # Should parse with --session
    args_yes = parser.parse_args(["--session", "sess-001"])
    assert args_yes.session == "sess-001"


def test_session_parent_creates_session_flag_required() -> None:
    """session_parent with required=True should make --session required."""
    from edison.core.utils.cli.arguments import session_parent

    parent = session_parent(required=True)
    parser = argparse.ArgumentParser(parents=[parent])

    # Should fail without --session
    with pytest.raises(SystemExit):
        parser.parse_args([])

    # Should succeed with --session
    args = parser.parse_args(["--session", "sess-001"])
    assert args.session == "sess-001"


def test_session_parent_custom_help_text() -> None:
    """session_parent should accept custom help text."""
    from edison.core.utils.cli.arguments import session_parent

    custom_help = "Custom session help text"
    parent = session_parent(help_text=custom_help)

    # Parser should have add_help=False
    assert parent.add_help is False

    # The help text should be used (we can verify this by checking the action)
    session_action = None
    for action in parent._actions:
        if "--session" in action.option_strings:
            session_action = action
            break

    assert session_action is not None
    assert session_action.help == custom_help


def test_session_parent_default_help_text() -> None:
    """session_parent should have sensible default help text."""
    from edison.core.utils.cli.arguments import session_parent

    parent = session_parent()

    # Find the session action
    session_action = None
    for action in parent._actions:
        if "--session" in action.option_strings:
            session_action = action
            break

    assert session_action is not None
    assert session_action.help is not None
    assert "session" in session_action.help.lower()


def test_dry_run_parent_creates_dry_run_flag() -> None:
    """dry_run_parent should create a parent parser with --dry-run flag."""
    from edison.core.utils.cli.arguments import dry_run_parent

    parent = dry_run_parent()
    parser = argparse.ArgumentParser(parents=[parent])

    # Without --dry-run
    args_no = parser.parse_args([])
    assert args_no.dry_run is False

    # With --dry-run
    args_yes = parser.parse_args(["--dry-run"])
    assert args_yes.dry_run is True


def test_dry_run_parent_custom_help_text() -> None:
    """dry_run_parent should accept custom help text."""
    from edison.core.utils.cli.arguments import dry_run_parent

    custom_help = "Custom dry run help"
    parent = dry_run_parent(help_text=custom_help)

    # Find the dry-run action
    dry_run_action = None
    for action in parent._actions:
        if "--dry-run" in action.option_strings:
            dry_run_action = action
            break

    assert dry_run_action is not None
    assert dry_run_action.help == custom_help


def test_dry_run_parent_default_help_text() -> None:
    """dry_run_parent should have sensible default help text."""
    from edison.core.utils.cli.arguments import dry_run_parent

    parent = dry_run_parent()

    # Find the dry-run action
    dry_run_action = None
    for action in parent._actions:
        if "--dry-run" in action.option_strings:
            dry_run_action = action
            break

    assert dry_run_action is not None
    assert dry_run_action.help is not None
    assert "preview" in dry_run_action.help.lower() or "dry" in dry_run_action.help.lower()


def test_parent_parsers_have_add_help_false() -> None:
    """Parent parsers should have add_help=False to avoid conflicts."""
    from edison.core.utils.cli.arguments import session_parent, dry_run_parent

    session = session_parent()
    dry_run = dry_run_parent()

    assert session.add_help is False
    assert dry_run.add_help is False


def test_multiple_parents_can_be_combined() -> None:
    """Multiple parent parsers should work together without conflicts."""
    from edison.core.utils.cli.arguments import session_parent, dry_run_parent, parse_common_args

    session = session_parent()
    dry_run = dry_run_parent()

    parser = argparse.ArgumentParser(parents=[session, dry_run])
    parse_common_args(parser)

    # All flags should be available
    args = parser.parse_args([
        "--session", "sess-001",
        "--dry-run",
        "--json",
        "-y",
        "--repo-root", "/tmp/test"
    ])

    assert args.session == "sess-001"
    assert args.dry_run is True
    assert args.json is True
    assert args.yes is True
    assert args.repo_root == Path("/tmp/test")
