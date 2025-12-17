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
    captured = capsys.readouterr()
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
