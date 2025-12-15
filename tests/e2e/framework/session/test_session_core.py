from __future__ import annotations

import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

from edison.core.exceptions import SessionError
from edison.core.session.core.id import validate_session_id
from edison.core.session.persistence.graph import save_session
from edison.core.session.persistence.repository import SessionRepository
from edison.core.session.lifecycle import manager as session_manager
from edison.core.utils.io.locking import LockTimeoutError, acquire_file_lock
from tests.helpers.timeouts import LOCK_TIMEOUT


def _run_edison(*argv: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    # Keep CLI execution deterministic for tests (some commands expect these to exist).
    env.setdefault("AGENTS_OWNER", "tester")
    env.setdefault("AGENTS_SESSION", "sess-test")
    return subprocess.run(
        ["python3", "-m", "edison", *argv],
        capture_output=True,
        text=True,
        env=env,
        cwd=Path.cwd(),
        check=False,
    )


def test_session_id_sanitization_blocks_path_traversal() -> None:
    malicious_ids = [
        "../../etc/passwd",
        "..\\..\\windows\\system32",
        "sess/../../secrets",
        "sess\\..\\..\\secrets",
        "../outside",
        "slash/in/id",
    ]
    for bad in malicious_ids:
        with pytest.raises(ValueError):
            validate_session_id(bad)


def test_create_session_writes_session_json() -> None:
    sid = "sess-core-001"
    path = session_manager.create_session(sid, owner="tester", create_wt=False)
    assert path.exists()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["id"] == sid
    assert data["state"]
    assert data["meta"]["owner"] == "tester"
    assert isinstance(data["meta"].get("createdAt"), str)
    assert isinstance(data["meta"].get("lastActive"), str)
    assert data["meta"]["status"] == data["state"]


def test_session_schema_persists_meta_extra_and_drops_unknown_top_level_keys() -> None:
    sid = "sess-core-002"
    session_manager.create_session(sid, owner="tester", create_wt=False)

    repo = SessionRepository()
    doc = repo.get_or_raise(sid).to_dict()

    doc["meta"]["customKey"] = "customValue"
    doc["topLevelCustom"] = "should_not_persist"
    save_session(sid, doc)

    reloaded = repo.get_or_raise(sid).to_dict()
    assert reloaded.get("meta", {}).get("customKey") == "customValue"
    assert "topLevelCustom" not in reloaded


def test_file_lock_timeout() -> None:
    sid = "sess-core-lock"
    session_manager.create_session(sid, owner="tester", create_wt=False)
    sess_path = SessionRepository().get_session_json_path(sid)

    with acquire_file_lock(sess_path, timeout=LOCK_TIMEOUT):
        with pytest.raises(LockTimeoutError):
            with acquire_file_lock(sess_path, timeout=LOCK_TIMEOUT / 2):
                pass


def test_session_recovery_cli_repairs_corrupted_session_json() -> None:
    sid = "sess-corrupt-001"
    session_manager.create_session(sid, owner="tester", create_wt=False)

    sess_path = SessionRepository().get_session_json_path(sid)
    sess_path.write_text("{bad json", encoding="utf-8")

    res = _run_edison("session", "recovery", "recover", "--session", sid)
    assert res.returncode == 0, f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"

    # After recovery, the session should live under recovery/ and be readable JSON again.
    repo = SessionRepository()
    recovered_path = repo.get_session_json_path(sid)
    data = json.loads(recovered_path.read_text(encoding="utf-8"))
    assert data.get("state") == "recovery"
    assert (recovered_path.parent / "session.json.corrupt").exists()


def test_archive_preserves_structure(tmp_path: Path) -> None:
    from edison.core.session import archive as session_archive

    sid = "sess-archive-001"
    session_manager.create_session(sid, owner="tester", create_wt=False)

    sess_dir = SessionRepository().get_session_json_path(sid).parent
    nested = sess_dir / "files" / "deep" / "branch" / "leaf.txt"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("hello", encoding="utf-8")

    archive_path = session_archive.archive_session(sid)
    assert archive_path.suffixes[-2:] == [".tar", ".gz"]

    with tarfile.open(archive_path, "r:gz") as tf:
        names = tf.getnames()
        assert any(name.endswith("files/deep/branch/leaf.txt") for name in names)


def test_get_session_errors_are_informative() -> None:
    sid = "sess-missing-001"

    # Create the directory but omit session.json to emulate a corrupted/missing record on disk.
    from edison.core.session._config import get_config

    cfg = get_config()
    initial_state = cfg.get_initial_session_state()
    dirname = cfg.get_session_states().get(initial_state, initial_state)
    raw_dir = Path(cfg.get_session_root_path()) / dirname / sid
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "session.json").unlink(missing_ok=True)

    with pytest.raises(SessionError, match=sid):
        session_manager.get_session(sid)
