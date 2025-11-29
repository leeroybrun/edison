import os
import sys
import json
import stat
from pathlib import Path

import pytest

from tests.helpers.paths import get_repo_root

_THIS_FILE = Path(__file__).resolve()
_CORE_ROOT = None
for _parent in _THIS_FILE.parents:
    candidate = _parent / ".edison" / "core"
    if (candidate / "lib").exists():
        _CORE_ROOT = candidate
        break

if _CORE_ROOT is None:
    _CORE_ROOT = get_repo_root()

CORE_ROOT = _CORE_ROOT
from tests.helpers import session as sessionlib  # type: ignore
from edison.core.utils import resilience  # type: ignore
from edison.core.config import ConfigManager


def test_missing_project_name_raises(monkeypatch: pytest.MonkeyPatch):
    """Test that missing PROJECT_NAME raises ValueError.

    Uses real environment setup instead of mocking.
    """
    # Remove PROJECT_NAME from environment
    monkeypatch.delenv("PROJECT_NAME", raising=False)

    # The real _get_project_name function should raise ValueError
    # when PROJECT_NAME is not set and get_project_name returns empty
    with pytest.raises(ValueError) as exc_info:
        sessionlib._get_project_name()

    # Verify error message is meaningful
    assert "PROJECT_NAME" in str(exc_info.value) or "required" in str(exc_info.value).lower()


def test_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError):
        sessionlib._get_database_url()


def test_invalid_yaml_config_fails_cleanly(tmp_path: Path):
    # Create a fake repo with .git and invalid edison.yaml
    (tmp_path / ".git").mkdir()
    (tmp_path / "edison.yaml").write_text("project: [this: is: invalid]", encoding="utf-8")
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
    repo_root = Path.cwd()
    rec_root = repo_root / ".project" / "sessions" / "recovery"
    rec_root.mkdir(parents=True, exist_ok=True)
    real = tmp_path / "recoverable"
    real.mkdir()
    (real / "session.json").write_text(json.dumps({"state": "Recovery"}), encoding="utf-8")
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
