import os
import json
import stat
from pathlib import Path

import pytest

from tests.helpers import session as sessionlib  # type: ignore
from edison.core.utils import resilience  # type: ignore
from edison.core.config import ConfigManager


def test_missing_project_name_raises(monkeypatch: pytest.MonkeyPatch):
    """Project name resolves via config (no required PROJECT_NAME env var)."""
    monkeypatch.delenv("PROJECT_NAME", raising=False)
    name = sessionlib._get_project_name()
    assert isinstance(name, str)
    assert name.strip()


def test_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch):
    """Database URL resolution fails closed when database.url is absent."""
    from edison.core.session.persistence.database import _get_database_url

    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError):
        _get_database_url({})


def test_invalid_yaml_config_fails_cleanly(tmp_path: Path):
    # Create a real git repo and invalid project config overlay under .edison/config/
    from tests.helpers.fixtures import create_repo_with_git
    create_repo_with_git(tmp_path)
    bad = tmp_path / ".edison" / "config" / "bad.yaml"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("project: [this: is: invalid", encoding="utf-8")
    cm = ConfigManager(repo_root=tmp_path)
    with pytest.raises(Exception):
        cm.load_config()


def test_missing_required_session_file_raises(tmp_path: Path):
    sess = tmp_path / "sess-missing-json"
    sess.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError):
        sessionlib.get_session_state(sess)


def test_malformed_session_json_raises(tmp_path: Path):
    sess = tmp_path / "sess-bad-json"
    sess.mkdir(parents=True, exist_ok=True)
    (sess / "session.json").write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        sessionlib.get_session_state(sess)


def test_permission_error_is_raised(tmp_path: Path):
    sess = tmp_path / "sess-perm"
    sess.mkdir(parents=True, exist_ok=True)
    (sess / "session.json").write_text(json.dumps({"state": "active"}), encoding="utf-8")
    # Remove read permissions
    os.chmod(sess / "session.json", 0)
    try:
        with pytest.raises(PermissionError):
            sessionlib.get_session_state(sess)
    finally:
        # Restore to allow cleanup on some systems
        os.chmod(sess / "session.json", stat.S_IRUSR | stat.S_IWUSR)


def test_include_recursion_prevention_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Create a recovery directory with a symlink causing potential cycles
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    rec_root = tmp_path / ".project" / "sessions" / "recovery"
    rec_root.mkdir(parents=True, exist_ok=True)
    real = tmp_path / "recoverable"
    real.mkdir()
    (real / "session.json").write_text(json.dumps({"state": "recovery"}), encoding="utf-8")
    (real / "recovery.json").write_text(json.dumps({"reason": "test"}), encoding="utf-8")
    # Symlink inside recovery pointing back to parent
    symlink = rec_root / "cycle"
    try:
        if not symlink.exists():
            symlink.symlink_to(rec_root, target_is_directory=True)
    except OSError:
        # Some systems may disallow symlinks; skip
        pytest.skip("symlinks not permitted on this filesystem")

    # Place the real session folder into recovery as well
    target = rec_root / "real"
    if target.exists():
        # ensure clean
        for p in target.rglob("*"):
            if p.is_file():
                p.unlink()
        target.rmdir()
    real.rename(target)

    # list_recoverable_sessions must not recurse into the symlink
    sessions = resilience.list_recoverable_sessions()
    names = [p.name for p in sessions]
    assert "cycle" not in names
    assert "real" in names
