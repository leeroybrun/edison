from __future__ import annotations

import argparse
import json


def test_session_create_inferred_collision_autosuffix(isolated_project_env, monkeypatch, capsys):
    """When session id is inferred and already exists, session create picks -seq-N."""
    from edison.cli.session import create as create_cli

    monkeypatch.setattr(create_cli, "generate_session_id", lambda: "fixed-pid-1")

    args = argparse.Namespace(
        session_id=None,
        owner="tester",
        mode="start",
        no_worktree=True,
        install_deps=False,
        base_branch=None,
        start_prompt=None,
        include_prompt_text=False,
        json=True,
        repo_root=None,
    )

    # First create: uses base id
    assert create_cli.main(args) == 0
    captured = capsys.readouterr()
    out1 = json.loads(captured.out or captured.err)
    assert out1["status"] == "created"
    assert out1["session_id"] == "fixed-pid-1"

    # Second create: same inferred base id -> should auto-suffix
    assert create_cli.main(args) == 0
    captured = capsys.readouterr()
    out2 = json.loads(captured.out or captured.err)
    assert out2["status"] == "created"
    assert out2["session_id"] == "fixed-pid-1-seq-1"


def test_session_create_explicit_existing_still_fails(isolated_project_env, monkeypatch, capsys):
    """Explicit --session-id collisions must remain fail-closed."""
    from edison.cli.session import create as create_cli

    # Create the session once.
    monkeypatch.setattr(create_cli, "generate_session_id", lambda: "fixed-pid-2")
    args_inferred = argparse.Namespace(
        session_id=None,
        owner="tester",
        mode="start",
        no_worktree=True,
        install_deps=False,
        base_branch=None,
        start_prompt=None,
        include_prompt_text=False,
        json=True,
        repo_root=None,
    )
    assert create_cli.main(args_inferred) == 0
    capsys.readouterr()

    # Now try explicit create with same id: must fail.
    args_explicit = argparse.Namespace(
        session_id="fixed-pid-2",
        owner="tester",
        mode="start",
        no_worktree=True,
        install_deps=False,
        base_branch=None,
        start_prompt=None,
        include_prompt_text=False,
        json=True,
        repo_root=None,
    )
    assert create_cli.main(args_explicit) == 1
    captured = capsys.readouterr()
    out = json.loads(captured.out or captured.err)
    assert out["error"] == "session_error"
