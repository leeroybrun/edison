"""Command execution helpers for E2E tests."""
from __future__ import annotations

import subprocess
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from edison.core.utils.subprocess import run_with_timeout
from edison.core.paths.resolver import PathResolver


def run_script(
    script_name: str,
    args: List[str],
    cwd: Path,
    check: bool = False,
    env: Optional[Dict[str, str]] = None
) -> subprocess.CompletedProcess:
    """Run an Edison CLI command by translating legacy script paths to new CLI commands.

    Legacy `.edison/core/scripts/*` paths are automatically mapped to `edison` CLI commands.

    Args:
        script_name: Script path (e.g., "tasks/ready", "session", "qa/new")
        args: Script arguments
        cwd: Working directory
        check: Raise exception on non-zero exit
        env: Environment variables

    Returns:
        CompletedProcess with stdout, stderr, returncode
    """
    # Map legacy script paths to new CLI commands (domain + command)
    script_mappings = {
        # Task commands
        "tasks/ready": ("task", "ready"),
        "tasks/new": ("task", "new"),
        "tasks/status": ("task", "status"),
        "tasks/claim": ("task", "claim"),
        "tasks/link": ("task", "link"),
        "tasks/split": ("task", "split"),
        "tasks/allocate-id": ("task", "allocate_id"),
        "tasks/ensure-followups": ("task", "ensure_followups"),
        "tasks/cleanup-stale-locks": ("task", "cleanup_stale_locks"),
        "tasks/mark-delegated": ("task", "mark_delegated"),
        "tasks/list": ("task", "list"),
        # Session commands
        "session": ("session", None),  # Special handling - subcommand in args
        "session/next": ("session", "next"),
        "session/start": ("session", "start"),
        "session/close": ("session", "close"),
        "session/create": ("session", "create"),
        "session/heartbeat": ("session", "track"),  # heartbeat is now track
        "session/track": ("session", "track"),
        # Tracking commands (aliased to session track)
        "track": ("session", "track"),
        # QA commands
        "qa/new": ("qa", "new"),
        "qa/promote": ("qa", "promote"),
        "qa/validate": ("qa", "validate"),
        "qa/round": ("qa", "round"),
        # Validators (aliases)
        "validators/validate": ("qa", "validate"),
        "validation/validate": ("qa", "validate"),
        # Compose commands
        "prompts/compose": ("compose", "all"),
        "compose/all": ("compose", "all"),
        # Config commands
        "config/show": ("config", "show"),
        # Git worktree commands
        "git/worktree-create": ("git", "worktree_create"),
        "git/worktree-cleanup": ("git", "worktree_cleanup"),
        "git/worktree-archive": ("git", "worktree_archive"),
        "git/worktree-list": ("git", "worktree_list"),
        # Rules commands
        "rules/show-for-context": ("rules", "show_for_context"),
    }

    # Get the CLI domain and command
    cli_parts = script_mappings.get(script_name)

    if not cli_parts:
        raise FileNotFoundError(
            f"Script not found: {script_name}\n"
            f"Available script mappings: {', '.join(sorted(script_mappings.keys()))}\n"
            f"Note: Legacy scripts have been migrated to Edison CLI."
        )

    domain, command = cli_parts

    # Handle special case where command is in args (e.g., "session" with ["new", ...])
    if command is None and args:
        # Map legacy session subcommands to new CLI commands
        session_subcommand_map = {
            "new": "create",
            "status": "status",
            "complete": "close",
            "next": "next",
            "start": "start",
            "close": "close",
            "heartbeat": "track",
            "track": "track",
        }
        subcommand = args[0]
        command = session_subcommand_map.get(subcommand, subcommand)
        args = args[1:]  # Remove subcommand from args

    if os.environ.get("DEBUG_CONTEXT7"):
        print(f"[DEBUG_CONTEXT7] running edison {domain} {command} (mapped from {script_name})", file=sys.stderr)

    # Run via the main edison CLI entry point
    cmd = ["edison", domain, command] + args

    test_env = os.environ.copy()
    if env:
        test_env.update(env)

    # Set AGENTS_PROJECT_ROOT to point to test repository root
    # This allows CLI scripts to use test environment instead of real repo
    test_env["AGENTS_PROJECT_ROOT"] = str(cwd)
    if os.environ.get("DEBUG_CONTEXT7"):
        print(f"[DEBUG_CONTEXT7] env -> DEBUG_CONTEXT7={test_env.get('DEBUG_CONTEXT7')}", file=sys.stderr)

    result = run_with_timeout(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
        env=test_env
    )
    return result


def assert_command_success(result: subprocess.CompletedProcess) -> None:
    """Assert command succeeded (exit code 0).

    Args:
        result: CompletedProcess from run_command or run_script

    Raises:
        AssertionError: If command failed
    """
    assert result.returncode == 0, (
        f"Command failed with exit code {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


def assert_command_failure(result: subprocess.CompletedProcess) -> None:
    """Assert command failed (non-zero exit code).

    Args:
        result: CompletedProcess from run_command or run_script

    Raises:
        AssertionError: If command succeeded
    """
    if os.environ.get("DEBUG_CONTEXT7"):
        print(f"[DEBUG_CONTEXT7] stdout={result.stdout!r} stderr={result.stderr!r} returncode={result.returncode}", file=sys.stderr)
    assert result.returncode != 0, (
        f"Command unexpectedly succeeded\n"
        f"STDOUT:\n{result.stdout}"
    )


def assert_output_contains(
    result: subprocess.CompletedProcess,
    expected: str,
    in_stderr: bool = False
) -> None:
    """Assert command output contains expected string.

    Args:
        result: CompletedProcess from run_command or run_script
        expected: Expected substring
        in_stderr: Check stderr instead of stdout

    Raises:
        AssertionError: If expected string not found
    """
    output = result.stderr if in_stderr else result.stdout
    assert expected in output, (
        f"Expected '{expected}' not found in {'stderr' if in_stderr else 'stdout'}\n"
        f"Output:\n{output}"
    )


def assert_error_contains(result: subprocess.CompletedProcess, expected: str) -> None:
    """Assert command stderr contains expected error string.

    Args:
        result: CompletedProcess from run_command or run_script
        expected: Expected error substring

    Raises:
        AssertionError: If expected error not found
    """
    assert expected in result.stderr, (
        f"Expected error '{expected}' not found in stderr\n"
        f"STDERR:\n{result.stderr}"
    )


def assert_json_output(result: subprocess.CompletedProcess) -> dict:
    """Assert command output is valid JSON and return parsed data.

    Args:
        result: CompletedProcess from run_command or run_script

    Returns:
        Parsed JSON data

    Raises:
        AssertionError: If output is not valid JSON
    """
    import json

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"Command output is not valid JSON: {e}\n"
            f"Output:\n{result.stdout}"
        )
