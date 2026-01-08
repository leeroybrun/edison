from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


def test_dispatcher_blocks_session_scoped_commands_outside_worktree_when_enforced(
    isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg_dir = isolated_project_env / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "worktrees.yml").write_text(
        yaml.safe_dump(
            {
                "worktrees": {
                    "enabled": True,
                    "baseBranchMode": "current",
                    "baseBranch": None,
                    "baseDirectory": str(tmp_path / "worktrees"),
                    "archiveDirectory": str(tmp_path / "worktrees" / "_archived"),
                    "branchPrefix": "session/",
                    "enforcement": {
                        "enabled": True,
                        "commands": ["session next", "session complete"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    # Ensure config caches reflect the file written above.
    from helpers.cache_utils import reset_edison_caches

    reset_edison_caches()

    from edison.core.config.manager import ConfigManager

    cm = ConfigManager(repo_root=isolated_project_env)
    assert cm.project_config_dir.resolve() == cfg_dir.resolve()
    assert (cm.project_config_dir / "worktrees.yml").exists()

    from edison.core.config.domains.session import SessionConfig

    wt_cfg = SessionConfig(repo_root=isolated_project_env).get_worktree_config()
    assert wt_cfg.get("baseDirectory") == str(tmp_path / "worktrees")
    assert (wt_cfg.get("enforcement") or {}).get("enabled") is True

    from edison.cli._dispatcher import main as cli_main

    # Create the session + worktree from the primary checkout.
    code = cli_main(
        [
            "session",
            "create",
            "--session-id",
            "sess-enforce",
            "--owner",
            "tester",
            "--json",
        ]
    )
    assert code == 0
    created = capsys.readouterr()
    payload = json.loads(created.out or "{}")
    session = payload.get("session") or {}
    git_meta = session.get("git") or {}
    wt = git_meta.get("worktreePath")
    assert isinstance(wt, str)
    wt_path = Path(wt).resolve()
    assert wt_path != isolated_project_env.resolve()
    assert wt_path.is_relative_to((tmp_path / "worktrees").resolve())

    # Running a session-scoped command from the primary checkout should be blocked.
    code2 = cli_main(["session", "next", "sess-enforce", "--json"])
    capsys.readouterr()
    # `session next` is read-only and should NOT be blocked (even when enforcement is enabled).
    assert code2 == 0

    # A mutating command should be blocked outside the worktree.
    code3 = cli_main(["session", "complete", "sess-enforce", "--json"])
    captured2 = capsys.readouterr()
    assert code3 == 2
    payload = json.loads(captured2.out or "{}")
    assert payload.get("error") == "worktree_enforcement"
    assert payload.get("command") == "session complete"
    assert payload.get("sessionId") == "sess-enforce"
    assert isinstance(payload.get("worktreePath"), str)


def test_dispatcher_allows_readonly_session_status_outside_worktree_when_enforced(
    isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Read-only `session status` must not be blocked by worktree enforcement."""
    cfg_dir = isolated_project_env / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "worktrees.yml").write_text(
        yaml.safe_dump(
            {
                "worktrees": {
                    "enabled": True,
                    "baseBranchMode": "current",
                    "baseBranch": None,
                    "baseDirectory": str(tmp_path / "worktrees"),
                    "archiveDirectory": str(tmp_path / "worktrees" / "_archived"),
                    "branchPrefix": "session/",
                    "enforcement": {"enabled": True, "commands": ["session status", "session complete"]},
                }
            }
        ),
        encoding="utf-8",
    )

    from helpers.cache_utils import reset_edison_caches

    reset_edison_caches()

    from edison.cli._dispatcher import main as cli_main

    code = cli_main(["session", "create", "--session-id", "sess-status", "--owner", "tester", "--json"])
    assert code == 0
    _created = capsys.readouterr()

    # Read-only status must not be blocked from the primary checkout.
    code2 = cli_main(["session", "status", "sess-status", "--json"])
    assert code2 == 0
    payload = json.loads(capsys.readouterr().out or "{}")
    assert payload.get("id") == "sess-status"


def test_worktree_enforcement_is_archive_aware(
    isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When a session worktree is archived, enforcement should guide restore (not dead `cd`)."""
    cfg_dir = isolated_project_env / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "worktrees.yml").write_text(
        yaml.safe_dump(
            {
                "worktrees": {
                    "enabled": True,
                    "baseBranchMode": "current",
                    "baseBranch": None,
                    "baseDirectory": str(tmp_path / "worktrees"),
                    "archiveDirectory": str(tmp_path / "worktrees" / "_archived"),
                    "branchPrefix": "session/",
                    "enforcement": {"enabled": True, "commands": ["session complete"]},
                }
            }
        ),
        encoding="utf-8",
    )

    from helpers.cache_utils import reset_edison_caches

    reset_edison_caches()

    from edison.cli._dispatcher import main as cli_main

    code = cli_main(["session", "create", "--session-id", "sess-arch", "--owner", "tester", "--json"])
    assert code == 0
    created = json.loads(capsys.readouterr().out or "{}")
    wt = ((created.get("session") or {}).get("git") or {}).get("worktreePath")
    assert isinstance(wt, str)

    # Archive the worktree but keep the session record pointing at the original path.
    from edison.core.session import worktree as worktree_lib

    archived_path = worktree_lib.archive_worktree("sess-arch", Path(wt))
    assert archived_path.exists()

    code2 = cli_main(["session", "complete", "sess-arch", "--json"])
    assert code2 == 2
    payload = json.loads(capsys.readouterr().out or "{}")
    assert payload.get("error") == "worktree_enforcement"
    assert payload.get("sessionId") == "sess-arch"
    assert payload.get("archivedWorktreePath") == str(archived_path.resolve())


def test_worktree_enforcement_blocks_evidence_capture_outside_worktree_for_session_scoped_task(
    isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Evidence capture must run in the session worktree to avoid stale snapshots."""
    cfg_dir = isolated_project_env / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "worktrees.yml").write_text(
        yaml.safe_dump(
            {
                "worktrees": {
                    "enabled": True,
                    "baseBranchMode": "current",
                    "baseBranch": None,
                    "baseDirectory": str(tmp_path / "worktrees"),
                    "archiveDirectory": str(tmp_path / "worktrees" / "_archived"),
                    "branchPrefix": "session/",
                    "enforcement": {"enabled": True, "commands": ["evidence capture"]},
                }
            }
        ),
        encoding="utf-8",
    )

    from helpers.cache_utils import reset_edison_caches

    reset_edison_caches()

    from edison.cli._dispatcher import main as cli_main

    code = cli_main(["session", "create", "--session-id", "sess-evidence", "--owner", "tester", "--json"])
    assert code == 0
    created = json.loads(capsys.readouterr().out or "{}")
    wt = ((created.get("session") or {}).get("git") or {}).get("worktreePath")
    assert isinstance(wt, str) and wt

    # Create a session-scoped task file (outside the worktree).
    session_tasks = isolated_project_env / ".project" / "sessions" / "wip" / "sess-evidence" / "tasks" / "wip"
    session_tasks.mkdir(parents=True, exist_ok=True)
    (session_tasks / "T-SESSION.md").write_text(
        "---\n"
        "id: T-SESSION\n"
        "title: Evidence worktree enforcement\n"
        "session_id: sess-evidence\n"
        "---\n\n"
        "Test task.\n",
        encoding="utf-8",
    )

    # From the primary checkout, evidence capture should be blocked.
    code2 = cli_main(["evidence", "capture", "T-SESSION", "--json"])
    assert code2 == 2
    payload = json.loads(capsys.readouterr().out or "{}")
    assert payload.get("error") == "worktree_enforcement"
    assert payload.get("command") == "evidence capture"
    assert payload.get("sessionId") == "sess-evidence"
