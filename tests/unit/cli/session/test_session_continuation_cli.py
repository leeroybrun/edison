from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_session(project_root: Path, session_id: str, *, state: str = "active") -> None:
    sessions_dir = project_root / ".project" / "sessions" / "wip" / session_id
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / "session.json"
    now = _now_iso()
    session_data = {
        "id": session_id,
        "meta": {
            "sessionId": session_id,
            "owner": "test-owner",
            "mode": "start",
            "status": state,
            "createdAt": now,
            "lastActive": now,
        },
        "state": state,
        "tasks": {},
        "qa": {},
        "git": {"worktreePath": None, "branchName": None, "baseBranch": None},
        "activityLog": [{"timestamp": now, "message": "Session created"}],
    }
    session_file.write_text(json.dumps(session_data, indent=2), encoding="utf-8")


def test_session_continuation_set_writes_meta_override(isolated_project_env: Path) -> None:
    from edison.cli.session.continuation.set import main, register_args

    sid = "s1"
    _write_session(isolated_project_env, sid)

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(
        [sid, "--mode", "hard", "--max-iterations", "5", "--json", "--repo-root", str(isolated_project_env)]
    )
    rc = main(args)
    assert rc == 0

    data = json.loads((isolated_project_env / ".project" / "sessions" / "wip" / sid / "session.json").read_text())
    cont = (data.get("meta") or {}).get("continuation") or {}
    assert cont.get("mode") == "hard"
    assert cont.get("maxIterations") == 5


def test_session_continuation_clear_removes_override(isolated_project_env: Path) -> None:
    from edison.cli.session.continuation.set import main as set_main, register_args as set_register
    from edison.cli.session.continuation.clear import main as clear_main, register_args as clear_register

    sid = "s2"
    _write_session(isolated_project_env, sid)

    set_parser = argparse.ArgumentParser()
    set_register(set_parser)
    set_args = set_parser.parse_args([sid, "--mode", "soft", "--json", "--repo-root", str(isolated_project_env)])
    assert set_main(set_args) == 0

    clear_parser = argparse.ArgumentParser()
    clear_register(clear_parser)
    clear_args = clear_parser.parse_args([sid, "--json", "--repo-root", str(isolated_project_env)])
    assert clear_main(clear_args) == 0

    data = json.loads((isolated_project_env / ".project" / "sessions" / "wip" / sid / "session.json").read_text())
    meta = data.get("meta") or {}
    assert "continuation" not in meta


def test_session_continuation_show_emits_effective_config(isolated_project_env: Path, capsys) -> None:
    from edison.cli.session.continuation.set import main as set_main, register_args as set_register
    from edison.cli.session.continuation.show import main as show_main, register_args as show_register

    sid = "s3"
    _write_session(isolated_project_env, sid)

    set_parser = argparse.ArgumentParser()
    set_register(set_parser)
    set_args = set_parser.parse_args(
        [sid, "--mode", "off", "--json", "--repo-root", str(isolated_project_env)]
    )
    assert set_main(set_args) == 0
    capsys.readouterr()

    show_parser = argparse.ArgumentParser()
    show_register(show_parser)
    show_args = show_parser.parse_args([sid, "--json", "--repo-root", str(isolated_project_env)])
    assert show_main(show_args) == 0

    out = capsys.readouterr().out
    payload = json.loads(out)
    effective = payload.get("effective") or {}
    assert effective.get("mode") == "off"
